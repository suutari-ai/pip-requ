import os

import mock
import pytest

from prequ._pip_compat import PIP_10_OR_NEWER, PIP_192_OR_NEWER, path_to_url
from prequ.exceptions import DependencyResolutionFailed
from prequ.repositories.pypi import PyPIRepository
from prequ.scripts._repo import get_pip_command

PY27_LINUX64_TAGS = [
    ('cp27', 'cp27mu', 'manylinux1_x86_64'),
    ('cp27', 'cp27mu', 'linux_x86_64'),
    ('cp27', 'none', 'manylinux1_x86_64'),
    ('cp27', 'none', 'linux_x86_64'),
    ('py2', 'none', 'manylinux1_x86_64'),
    ('py2', 'none', 'linux_x86_64'),
    ('cp27', 'none', 'any'),
    ('cp2', 'none', 'any'),
    ('py27', 'none', 'any'),
    ('py2', 'none', 'any'),
    ('py26', 'none', 'any'),
    ('py25', 'none', 'any'),
    ('py24', 'none', 'any'),
    ('py23', 'none', 'any'),
    ('py22', 'none', 'any'),
    ('py21', 'none', 'any'),
    ('py20', 'none', 'any'),
]


def _patch_supported_tags(func):
    if PIP_10_OR_NEWER:
        def get_supported_tags(versions=None, noarch=False, platform=None,
                               impl=None, abi=None):
            return PY27_LINUX64_TAGS

        to_patch = 'pip._internal.' + (
            'models.target_python.get_supported' if PIP_192_OR_NEWER else
            'pep425tags.get_supported')
        return mock.patch(
            to_patch,
            new=get_supported_tags)(func)
    else:
        return mock.patch(
            'pip.pep425tags.supported_tags',
            new=PY27_LINUX64_TAGS)(func)


@_patch_supported_tags
def test_resolving_respects_platform(from_line):
    repository = get_repository()
    if hasattr(repository.finder, 'candidate_evaluator'):
        repository.finder.candidate_evaluator._valid_tags = PY27_LINUX64_TAGS
    else:
        repository.finder.valid_tags = PY27_LINUX64_TAGS

    ireq = from_line('cryptography==2.0.3')
    deps = repository.get_dependencies(ireq)
    assert 'enum34' in set(x.name for x in deps)
    assert 'ipaddress' in set(x.name for x in deps)


def test_generate_hashes_only_current_platform(from_line):
    all_cffi_191_hashes = {
        'sha256:04b133ef629ae2bc05f83d0b079a964494a9cd17914943e690c57209b44aae20',
        'sha256:0f1b3193c17b93c75e73eeac92f22eec4c98a021d9969b1c347d1944fae0d26b',
        'sha256:1fb1cf40c315656f98f4d3acfb1bd031a14a9a69d155e9a180d5f9b52eaf745a',
        'sha256:20af85d8e154b50f540bc8d517a0dbf6b1c20b5d06e572afda919d5dafd1d06b',
        'sha256:2570f93b42c61013ab4b26e23aa25b640faf5b093ad7dd3504c3a8eadd69bc24',
        'sha256:2f4e2872833ee3764dfc168dea566b7dd83b01ac61b377490beba53b5ece57f7',
        'sha256:31776a37a67424e7821324b9e03a05aa6378bbc2bccc58fa56402547f82803c6',
        'sha256:353421c76545f1d440cacc137abc865f07eab9df0dd3510c0851a2ca04199e90',
        'sha256:36d06de7b09b1eba54b1f5f76e2221afef7489cc61294508c5a7308a925a50c6',
        'sha256:3f1908d0bcd654f8b7b73204f24336af9f020b707fb8af937e3e2279817cbcd6',
        'sha256:5268de3a18f031e9787c919c1b9137ff681ea696e76740b1c6c336a26baaa58a',
        'sha256:563e0bd53fda03c151573217b3a49b3abad8813de9dd0632e10090f6190fdaf8',
        'sha256:5e1368d13f1774852f9e435260be19ad726bbfb501b80472f61c2dc768a0692a',
        'sha256:60881c79eb72cb75bd0a4be5e31c9e431739146c4184a2618cabea3938418984',
        'sha256:6120b62a642a40e47eb6c9ff00c02be69158fc7f7c5ff78e42a2c739d1c57cd6',
        'sha256:65c223e77f87cb463191ace3398e0a6d84ce4ac575d42eb412a220b099f593d6',
        'sha256:6fbf8db55710959344502b58ab937424173ad8b5eb514610bcf56b119caa350a',
        'sha256:74aadea668c94eef4ceb09be3d0eae6619e28b4f1ced4e29cd43a05bb2cfd7a4',
        'sha256:7be1efa623e1ed91b15b1e62e04c536def1d75785eb930a0b8179ca6b65ed16d',
        'sha256:83266cdede210393889471b0c2631e78da9d4692fcca875af7e958ad39b897ee',
        'sha256:86c68a3f8246495962446c6f96f6a27f182b91208187b68f1e87ec3dfd29fa32',
        'sha256:9163f7743cf9991edaddf9cf886708e288fab38e1b9fec9c41c15c85c8f7f147',
        'sha256:97d9f338f91b7927893ea6500b953e4b4b7e47c6272222992bb76221e17056ff',
        'sha256:a7930e73a4359b52323d09de6d6860840314aa09346cbcf4def8875e1b07ebc7',
        'sha256:ada8a42c493e4934a1a8875c2bc9efcb1b88c09883f70375bfa053ab32d6a118',
        'sha256:b0bc2d83cc0ba0e8f0d9eca2ffe07f72f33bec7d84547071e7e875d4cca8272d',
        'sha256:b5412a65605c642adf3e1544b59b8537daf5696dedadd2b3cbebc42e24da45ed',
        'sha256:ba6b5205fced1625b6d9d55f9ef422f9667c5d95f18f07c0611eb964a3355331',
        'sha256:bcaf3d86385daaab0ae51c9c53ebe70a6c1c5dfcb9e311b13517e04773ddf6b6',
        'sha256:cfa15570ecec1ea6bee089e86fd4deae6208c96a811344ce246de5e5c9ac824a',
        'sha256:d3e3063af1fa6b59e255da9a812891cdaf24b90fbaf653c02797871069b7c4c9',
        'sha256:d9cfe26ecea2fec320cd0cac400c9c2435328994d23596ee6df63945fe7292b0',
        'sha256:e5ef800ef8ef9ee05ae9a5b7d7d9cf7d6c936b32e312e54823faca3034ee16ab',
        'sha256:f1366150acf611d09d37ffefb3559ed3ffeb1713643d3cd10716d6c5da3f83fb',
        'sha256:f4eb9747a37120b35f59c8e96265e87b0c432ff010d32fc0772992aa14659502',
        'sha256:f8264463cc08cd696ad17e4bf3c80f3344628c04c11ffdc545ddf0798bc17316',
        'sha256:f8ba54848dfe280b1be0d6e699544cee4ba10d566f92464538063d9e645aed3e',
        'sha256:f93d1edcaea7b6a7a8fbf936f4492a9a0ee0b4cb281efebd5e1dd73e5e432c71',
        'sha256:fc8865c7e0ac25ddd71036c2b9a799418b32d9acb40400d345b8791b6e1058cb',
        'sha256:fce6b0cb9ade1546178c031393633b09c4793834176496c99a94de0bfa471b27',
        'sha256:fde17c52d7ce7d55a9fb263b57ccb5da6439915b5c7105617eb21f636bb1bd9c',
    }

    repository = get_repository()
    ireq = from_line('cffi==1.9.1')
    hashes = repository.get_hashes(ireq)
    assert hashes != all_cffi_191_hashes, "No platform could support them all"
    assert hashes.issubset(all_cffi_191_hashes)


def test_generate_hashes_without_interfering_with_each_other(from_line):
    repository = get_repository()
    repository.get_hashes(from_line('cffi==1.9.1'))
    repository.get_hashes(from_line('matplotlib==2.0.2'))


def test_get_hashes_non_pinned(from_line):
    repository = get_repository()
    with pytest.raises(ValueError):
        repository.get_hashes(from_line('prequ'))


def test_get_dependencies_non_pinned_non_editable(from_line):
    repository = get_repository()
    with pytest.raises(TypeError):
        repository.get_dependencies(from_line('prequ'))


def test_failing_setup_script(from_editable):
    repository = get_repository()
    failing_package_dir = os.path.join(
        os.path.split(__file__)[0], 'test_data', 'failing_package')
    failing_package_url = path_to_url(failing_package_dir)
    ireq = from_editable(failing_package_url)

    with pytest.raises(DependencyResolutionFailed) as excinfo:
        repository.get_dependencies(ireq)

    # Check the contents of the error message
    error_message = '{}'.format(excinfo.value)
    assert error_message.startswith(
        'Dependency resolution of {url} failed:\n'.format(
            url=failing_package_url))

    egg_info_failed = 'Command "python setup.py egg_info" failed'
    command_errored = (
        'Command errored out with exit status 1:'
        ' python setup.py egg_info Check the logs for full command output.')
    assert (
        egg_info_failed in error_message
        or
        command_errored in error_message)

    import_error = "No module named 'non_existing_setup_helper'"
    import_error2 = import_error.replace("'", '')  # On Python 2
    assert (import_error in error_message) or (import_error2 in error_message)


def get_repository():
    pip_command = get_pip_command()
    pip_options, _ = pip_command.parse_args([
        '--index-url', PyPIRepository.DEFAULT_INDEX_URL
    ])
    session = pip_command._build_session(pip_options)
    return PyPIRepository(pip_options, session)


def test_get_hashes_editable_empty_set(from_editable):
    pip_command = get_pip_command()
    pip_options, _ = pip_command.parse_args([
        '--index-url', PyPIRepository.DEFAULT_INDEX_URL
    ])
    session = pip_command._build_session(pip_options)
    repository = PyPIRepository(pip_options, session)
    ireq = from_editable('git+https://github.com/django/django.git#egg=django')
    assert repository.get_hashes(ireq) == set()
