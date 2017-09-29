import os
from textwrap import dedent
from six.moves.urllib.request import pathname2url
import subprocess
import sys
import shutil
import mock

from click.testing import CliRunner

import pytest
from piptools.scripts.compile import cli
from piptools.scripts.sync import cli as sync_cli


@pytest.yield_fixture
def pip_conf(tmpdir):
    test_conf = dedent("""\
        [global]
        index-url = http://example.com
        trusted-host = example.com
    """)

    pip_conf_file = 'pip.conf' if os.name != 'nt' else 'pip.ini'
    path = (tmpdir / pip_conf_file).strpath

    with open(path, 'w') as f:
        f.write(test_conf)

    old_value = os.environ.get('PIP_CONFIG_FILE')
    try:
        os.environ['PIP_CONFIG_FILE'] = path
        yield path
    finally:
        if old_value is not None:
            os.environ['PIP_CONFIG_FILE'] = old_value
        else:
            del os.environ['PIP_CONFIG_FILE']
        os.remove(path)


def test_default_pip_conf_read(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        # preconditions
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v'])

        # check that we have our index-url as specified in pip.conf
        assert 'Using indexes:\n  http://example.com' in out.output
        assert '--index-url http://example.com' in out.output


def test_command_line_overrides_pip_conf(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        # preconditions
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v', '-i', 'http://override.com'])

        # check that we have our index-url as specified in pip.conf
        assert 'Using indexes:\n  http://override.com' in out.output


def test_command_line_setuptools_read():
    runner = CliRunner()
    with runner.isolated_filesystem():
        package = open('setup.py', 'w')
        package.write(dedent("""\
            from setuptools import setup
            setup(install_requires=[])
        """))
        package.close()
        out = runner.invoke(cli)

        # check that pip-compile generated a configuration
        assert 'This file is autogenerated by pip-compile' in out.output


def test_find_links_option(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        open('requirements.in', 'w').close()
        find_link_options = [
            '-f', './libs1',
            '-f', '/global-libs',
            '-f', './libs2',
        ]
        out = runner.invoke(cli, ['-v'] + find_link_options)

        # Check that find-links has been passed to pip
        assert ('Configuration:\n'
                '  -f ./libs1\n'
                '  -f /global-libs\n'
                '  -f ./libs2\n') in out.output

        assert ('--find-links libs1\n'
                '--find-links libs2\n') in out.output


def test_extra_index_option(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v',
                                  '--extra-index-url', 'http://extraindex1.com',
                                  '--extra-index-url', 'http://extraindex2.com'])
        assert ('Using indexes:\n'
                '  http://example.com\n'
                '  http://extraindex1.com\n'
                '  http://extraindex2.com' in out.output)
        assert ('--index-url http://example.com\n'
                '--extra-index-url http://extraindex1.com\n'
                '--extra-index-url http://extraindex2.com' in out.output)


def test_trusted_host(pip_conf):
    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v',
                                  '--trusted-host', 'example.com',
                                  '--trusted-host', 'example2.com'])
        assert ('--trusted-host example.com\n'
                '--trusted-host example2.com\n' in out.output)


def test_trusted_host_no_emit(pip_conf):
    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v',
                                  '--trusted-host', 'example.com',
                                  '--no-emit-trusted-host'])
        assert '--trusted-host example.com' not in out.output
        assert '--no-emit-trusted-host' in out.output


def test_realistic_complex_sub_dependencies(tmpdir):

    # make a temporary wheel of a fake package
    subprocess.check_output(['pip', 'wheel',
                             '--no-deps',
                             '-w', str(tmpdir),
                             os.path.join('.', 'tests', 'fixtures', 'fake_package', '.')])

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements.in', 'w') as req_in:
            req_in.write('fake_with_deps')  # require fake package

        out = runner.invoke(cli, ['-v',
                                  '-n', '--rebuild',
                                  '-f', str(tmpdir)])

        assert out.exit_code == 0


def _invoke(command):
    """Invoke sub-process."""
    try:
        output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
        )
        status = 0
    except subprocess.CalledProcessError as error:
        output = error.output
        status = error.returncode

    return status, output


def test_run_as_module_compile():
    """piptools can be run as ``python -m piptools ...``."""

    status, output = _invoke([
        sys.executable, '-m', 'piptools', 'compile', '--help',
    ])

    # Should have run pip-compile successfully.
    output = output.decode('utf-8')
    assert output.startswith('Usage:')
    assert 'Compiles requirements.txt from requirements.in' in output
    assert status == 0


def test_run_as_module_sync():
    """piptools can be run as ``python -m piptools ...``."""

    status, output = _invoke([
        sys.executable, '-m', 'piptools', 'sync', '--help',
    ])

    # Should have run pip-compile successfully.
    output = output.decode('utf-8')
    assert output.startswith('Usage:')
    assert 'Synchronize virtual environment with' in output
    assert status == 0


def test_sync_quiet(tmpdir):
    """sync command can be run with `--quiet` or `-q` flag."""

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements.txt', 'w') as req_in:
            req_in.write('six==1.10.0')

        with mock.patch('piptools.sync.check_call') as check_call:
            out = runner.invoke(sync_cli, ['-q'])
            assert out.output == ''
            assert out.exit_code == 0
            # for every call to pip ensure the `-q` flag is set
            for call in check_call.call_args_list:
                assert '-q' in call[0][0]


def test_editable_package(small_fake_package_dir):
    """ piptools can compile an editable """
    small_fake_package_dir = 'file:' + pathname2url(small_fake_package_dir)
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements.in', 'w') as req_in:
            req_in.write('-e ' + small_fake_package_dir)  # require editable fake package

        out = runner.invoke(cli, ['-n'])

        assert out.exit_code == 0
        assert small_fake_package_dir in out.output
        assert 'six==1.10.0' in out.output


def test_editable_package_vcs(tmpdir):
    vcs_package = (
        'git+git://github.com/pytest-dev/pytest-django'
        '@21492afc88a19d4ca01cd0ac392a5325b14f95c7'
        '#egg=pytest-django'
    )
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements.in', 'w') as req_in:
            req_in.write('-e ' + vcs_package)
        out = runner.invoke(cli, ['-n',
                                  '--rebuild'])
        print(out.output)
        assert out.exit_code == 0
        assert vcs_package in out.output
        assert 'pytest' in out.output  # dependency of pytest-django


def test_relative_editable_package(small_fake_package_dir):
    # fake_package_dir = 'file:' + pathname2url(fake_package_dir)
    runner = CliRunner()
    with runner.isolated_filesystem() as loc:
        new_package_dir = os.path.join(loc, 'small_fake_package')
        # Move the small_fake_package inside the temp directory
        shutil.copytree(small_fake_package_dir, new_package_dir)
        relative_package_dir = os.path.relpath(new_package_dir)
        relative_package_req = '-e file:' + os.path.join('.', relative_package_dir)

        with open('requirements.in', 'w') as req_in:
            req_in.write('-e ' + 'small_fake_package')  # require editable fake package

        out = runner.invoke(cli, ['-n'])

        print(out.output)
        assert out.exit_code == 0
        assert relative_package_req in out.output


def test_input_file_without_extension():
    """
    piptools can compile a file without an extension,
    and add .txt as the defaut output file extension.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements', 'w') as req_in:
            req_in.write('six==1.10.0')

        out = runner.invoke(cli, ['-n', 'requirements'])

        assert out.exit_code == 0
        assert '--output-file requirements.txt' in out.output
        assert 'six==1.10.0' in out.output


def test_upgrade_packages_option(minimal_wheels_dir):
    """
    piptools respects --upgrade-package/-P inline list.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements.in', 'w') as req_in:
            req_in.write('small-fake-a\nsmall-fake-b')
        with open('requirements.txt', 'w') as req_in:
            req_in.write('small-fake-a==0.1\nsmall-fake-b==0.1')

        out = runner.invoke(cli, [
            '-P', 'small_fake_b',
            '-f', minimal_wheels_dir,
        ])

        assert out.exit_code == 0
        assert 'small-fake-a==0.1' in out.output
        assert 'small-fake-b==0.2' in out.output
