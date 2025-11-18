""" ae_console unit tests. """
import datetime
import logging
import os

import pytest
import sys
import threading
import time

from typing import cast, Any
from unittest.mock import patch

from conftest import skip_gitlab_ci, delete_files

from ae.base import DATE_ISO, DATE_TIME_ISO, INI_EXT, UNSET, norm_name, os_user_name, write_file
from ae.paths import normalize
# noinspection PyProtectedMember
from ae.core import (DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE, MAX_NUM_LOG_FILES,
                     activate_multi_threading, _deactivate_multi_threading, main_app_instance, print_out)

from ae.console import MAIN_SECTION_NAME, USER_NAME_MAX_LEN, config_value_string, ConsoleApp


@pytest.fixture
def config_fna_vna_vva(request):
    """ prepare config test files """
    def _setup_and_teardown(file_name="test_config" + INI_EXT, var_name='test_config_var',
                            var_value: Any = 'test_value', additional_line: str = ""):
        file_name = normalize(file_name)
        write_file(file_name, f"[{MAIN_SECTION_NAME}]\n{var_name} = {var_value}\n{additional_line}", make_dirs=True)

        def _tear_down():               # using yield instead of finalizer does not execute the teardown part
            if os.path.exists(file_name):       # some tests are deleting the config file explicitly
                os.remove(file_name)
        request.addfinalizer(_tear_down)

        return file_name, var_name, var_value

    return _setup_and_teardown


class TestHelpers:
    def test_config_value_string(self):
        assert config_value_string(369) == "369"
        assert config_value_string(369.3) == "369.3"
        assert config_value_string('string') == "'string'"
        assert config_value_string({}) == "{}"
        assert config_value_string(dict(a=1)) == "{'a': 1}"
        assert config_value_string([]) == "[]"
        assert config_value_string(list('b')) == "['b']"
        assert config_value_string(tuple()) == "()"
        assert config_value_string(tuple((3, 'a', 2.1))) == "(3, 'a', 2.1)"
        value = datetime.date(2020, 11, 3)
        assert config_value_string(value) == value.strftime(DATE_ISO)
        value = datetime.datetime(2020, 11, 3)
        assert config_value_string(value) == value.strftime(DATE_TIME_ISO)


class TestLogging:      # more detailed logging tests are done in unit tests of :mod:`ae.core`
    def test_logging_params_dict_basic_from_cfg(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, var_val = config_fna_vna_vva(var_name='py_logging_params',
                                                          var_value=dict(version=1,
                                                                         disable_existing_loggers=False))

        cae = ConsoleApp('test_python_logging_params_dict_basic_from_ini', additional_cfg_files=[file_name])

        cfg_val = cae.get_variable(var_name)
        assert cfg_val == var_val

        assert cae.py_log_params == var_val

        logging.shutdown()

    def test_open_log_file_with_suppressed_stdout(self, capsys, restore_app_env):
        cae = ConsoleApp('test_log_file_rotation', suppress_stdout=True)
        assert cae.suppress_stdout is True
        cae.po("tst_out")
        cae.init_logging()      # close log file
        assert capsys.readouterr()[0] == ""

    def test_open_log_file_with_suppressed_stdout_and_log_file(self, capsys, restore_app_env):
        log_file = 'test_sup_std_out.log'
        tst_out = "tst_out"
        try:
            cae = ConsoleApp('test_log_file_rotation_with_log', suppress_stdout=True, log_file_name=log_file)
            assert cae.suppress_stdout is True
            cae.po(tst_out)
            cae.init_logging()      # close log file
            assert os.path.exists(log_file)
            assert capsys.readouterr()[0] == ""
        finally:
            content = delete_files(log_file, ret_type="contents")
            assert tst_out in content[0]

    def test_cae_log_file_rotation(self, restore_app_env):
        log_file = 'test_cae_rot_log.log'
        cae = ConsoleApp('test_cae_log_file_rotation',
                         multi_threading=True,
                         log_file_name=log_file,
                         log_file_size_max=.001)
        try:
            sys.argv = [restore_app_env, ]
            file_name_chk = cae.get_option('log_file')   # has to be called at least once to create log file
            assert file_name_chk == log_file
            for idx in range(MAX_NUM_LOG_FILES + 9):
                for line_no in range(16):     # full loop is creating 1 kb of log entries (16 * 64 bytes)
                    cae.po("TestCaeLogEntry{: >26}{: >26}".format(idx, line_no))
            cae.init_logging()      # close log file
            assert os.path.exists(log_file)
        finally:
            assert delete_files(log_file, keep_ext=True) >= MAX_NUM_LOG_FILES

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_logging_params_dict_from_cfg(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, var_val = config_fna_vna_vva(var_name='logging_params',
                                                          var_value=dict(log_file_name='test_log_from_cfg.log'))
        log_msg = "test log message"

        cae = ConsoleApp('test_ae_logging_params_dict_from_ini',
                         additional_cfg_files=[file_name],
                         debug_level=DEBUG_LEVEL_DISABLED)
        assert cae._main_cfg_fnam == file_name

        cfg_val = cae.get_variable(var_name)
        try:
            assert cfg_val == var_val
            assert cae.get_variable(var_name) == var_val
            assert cae._log_file_name == os.path.realpath(cfg_val['log_file_name'])
            assert not os.path.exists(cfg_val['log_file_name'])

            cae.po(log_msg)
            assert os.path.exists(cfg_val['log_file_name'])

            logging.shutdown()
        finally:
            assert delete_files(cfg_val['log_file_name'], ret_type="contents")[0].endswith(log_msg)

    def test_app_instances_reset2(self):
        assert main_app_instance() is None

    def test_app_instances_reset3(self):
        assert main_app_instance() is None

    def test_log_file_flush(self, restore_app_env):
        log_file = 'test_ae_log_flush.log'
        cae = ConsoleApp('test_log_file_flush', log_file_name=log_file)
        try:
            sys.argv = [restore_app_env, ]
            file_name_chk = cae.get_option('log_file')   # has to be called at least once to create log file
            assert file_name_chk == log_file
            assert os.path.exists(log_file)
        finally:
            assert delete_files(log_file) == 1

    def test_sub_app_logging(self, restore_app_env):
        log_file = 'test_sub_app_logging.log'
        tst_out = 'print-out to log file'
        mp = "MAIN_"  # main/sub-app prefixes for log file names and print-outs
        sp = "SUB__"
        try:
            app = ConsoleApp('test_main_app', app_name=mp)
            app.init_logging(log_file_name=mp + log_file)
            sub = ConsoleApp('test_sub_app', app_name=sp)
            sub.init_logging(log_file_name=sp + log_file)
            print_out(mp + tst_out + "_1")
            app.po(mp + tst_out + "_2")
            sub.po(sp + tst_out)
            sub.init_logging()
            app.init_logging()  # close log file
            # NOT WORKING: capsys.readouterr() returning empty strings
            # out, err = capsys.readouterr()
            # assert out.count(tst_out) == 3 and err == ""
            assert os.path.exists(mp + log_file)
            assert os.path.exists(sp + log_file)
        finally:
            contents = delete_files(sp + log_file, ret_type='contents')
            assert len(contents)
            assert mp + tst_out + "_1" in contents[0]
            assert mp + tst_out + "_2" in contents[0]
            assert sp + tst_out in contents[0]
            contents = delete_files(mp + log_file, ret_type='contents')
            assert len(contents)
            assert mp + tst_out + "_1" in contents[0]   # failing sometimes ?!?!?
            assert mp + tst_out + "_2" in contents[0]
            assert sp + tst_out not in contents[0]

    @skip_gitlab_ci
    def disabled___test_threaded_sub_app_logging(self, ___restore_app_env):
        sub_printed = False
        # thread_started_event = threading.Event()

        def sub_app_po():
            """ sub-app thread function """
            nonlocal sub_app, sub_printed
            sub_app = ConsoleApp('test_sub_app_thread', app_name=sp)
            sub_app.init_logging(log_file_name=sp + log_file)
            sub_app.po(sp + tst_out)
            sub_printed = True
            # thread_started_event.set()

        log_file = 'test_threaded_sub_app_logging.log'
        tst_out = 'print-out to log file'
        mp = "MAIN_"  # main/sub-app prefixes for log file names and print-outs
        sp = "SUB__"
        try:
            mai_app = ConsoleApp('test_main_app_thread', app_name=mp, multi_threading=True)
            mai_app.init_logging(log_file_name=mp + log_file)
            sub_app = None
            sub_thread = threading.Thread(target=sub_app_po)
            sub_thread.start()
            # assert thread_started_event.wait(timeout=6)
            while not sub_printed:  # NOT ENOUGH/failing on gitlab ci with: not sub_app or not sub_app.active_log_stream
                pass            # wait until sub-thread has called init_logging()/hangs in PyCharm DEBUG test run?!?!?
            print_out(mp + tst_out + "_1")
            mai_app.po(mp + tst_out + "_2")
            assert mai_app is main_app_instance()
            assert mai_app.is_main_app
            assert sub_app is not None
            # noinspection PyUnresolvedReferences,PyUnreachableCode
            assert not sub_app.is_main_app
            # noinspection PyUnresolvedReferences,PyUnreachableCode
            sub_app.init_logging()  # close sub-app log file
            # noinspection PyUnreachableCode
            sub_thread.join()
            # noinspection PyUnreachableCode
            mai_app.init_logging()  # close main-app log file
            # noinspection PyUnreachableCode
            assert os.path.exists(sp + log_file)
            # noinspection PyUnreachableCode
            assert os.path.exists(mp + log_file)
        finally:
            contents = delete_files(mp + log_file, ret_type='contents')
            assert len(contents)
            assert sp + tst_out not in contents[0]
            assert mp + tst_out + "_1" in contents[0]
            assert mp + tst_out + "_2" in contents[0]
            contents = delete_files(sp + log_file, ret_type='contents')
            assert len(contents)
            assert sp + tst_out in contents[0]
            assert mp + tst_out + "_1" in contents[0]
            assert mp + tst_out + "_2" in contents[0]

    def test_exception_log_file_flush(self, restore_app_env):
        cae = ConsoleApp('test_exception_log_file_flush')
        # cause/provoke _append_eof_and_flush_file() exceptions for coverage by passing any other non-stream object
        # noinspection PyTypeHints,PyUnresolvedReferences
        cae._append_eof_and_flush_file(cast('TextIO', None), 'invalid stream')

    def test_app_instances_reset_fin(self):
        assert main_app_instance() is None


class TestConfigOptions:
    def test_missing_cfg_file(self, restore_app_env):
        file_name = 'm_i_s_s_i_n_g' + INI_EXT
        cae = ConsoleApp('test_missing_cfg_file', additional_cfg_files=[file_name])
        assert not [f for f in cae._cfg_files if f.endswith(file_name)]

    def test_add_option(self, restore_app_env):
        cae = ConsoleApp('test_add_opt')
        opt_name = 'test_opt'
        opt_val = 'test_opt_value'

        assert cae.get_option(opt_name) is None

        cae.add_option(opt_name, 'test_opt_description', opt_val)

        assert cae.get_option(opt_name) == opt_val

    def test_add_argument(self, restore_app_env):
        cae = ConsoleApp('test_add_argument')
        cae.add_argument('test_arg')

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_del_section(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_del_section', additional_cfg_files=[file_name])
        val = 'any_tst_val'
        section_name = 'tstSection'
        assert cae.set_variable(var_name, val, cfg_fnam=file_name, section=section_name) == ""
        assert val == cae.get_variable(var_name, section=section_name)

        assert cae.del_section(section_name, cfg_fnam=file_name) == ""

        assert cae.get_variable(var_name, section=section_name) is None

    def test_del_section_not_exists(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_del_section_not_exists', additional_cfg_files=[file_name])
        section_name = 'tstNotExistingSection'
        assert cae.get_variable(var_name, section=section_name) is None

        err_msg = cae.del_section(section_name, cfg_fnam=file_name)

        assert file_name in err_msg
        assert section_name in err_msg

    def test_del_section_no_file(self, cons_app):
        cae = cons_app
        section_name = 'not_existing_section'
        fil_nam = 'no_existing_file'

        err_msg = cae.del_section(section_name, cfg_fnam=fil_nam)

        assert "del_section" in err_msg
        assert section_name in err_msg
        assert fil_nam in err_msg

    def test_get_argument(self, restore_app_env):
        cae = ConsoleApp('test_get_argument')
        cae.add_argument('test_arg')
        arg_val = 'test_arg_val'
        sys.argv = ['test_app', arg_val]
        assert cae.get_argument('test_arg') == arg_val

    def test_get_option(self, capsys, cons_app):
        assert cons_app.get_option('force') is 0
        assert cons_app.get_option('name_of_undefined_opt') is None
        assert cons_app.get_option('name_of_undefined_opt', default_value='value_of_opt') == 'value_of_opt'

        out, err = capsys.readouterr()
        assert 'ConsoleApp.get_option call before explicit command line args parsing' in out
        assert 'force' in out
        assert err == ""

    def test_get_variable_basics(self, cons_app):
        cae = cons_app
        assert cae.get_variable('debug_level') == DEBUG_LEVEL_VERBOSE
        assert cae.get_variable('un_declared_name') is None

    def test_get_variable_env_options(self, cons_app):
        cae = cons_app
        vn = 'testVarName'
        assert cae.get_variable(vn) is None

        vv = 'testVarValue'
        os.environ['AE_OPTIONS_TEST_VAR_NAME'] = vv
        assert cae.get_variable(vn) == vv

    def test_get_variable_env_section(self, cons_app):
        cae = cons_app
        vn = 'testVarName'
        assert cae.get_variable(vn, section='aeSystems') is None

        vv = 'testVarValue'
        os.environ['AE_SYSTEMS_TEST_VAR_NAME'] = vv
        assert cae.get_variable(vn, section='aeSystems') == vv

    @skip_gitlab_ci     # skip on gitlab because it does not provide user/home ~/.config folder
    def test_get_variable_file_order(self, restore_app_env, config_fna_vna_vva):
        cwd_file, var_name, cwd_value = config_fna_vna_vva(file_name='test' + INI_EXT, var_value='cwd')
        cae = ConsoleApp('test_get_variable_file_order', app_name='test')  # not needed: additional_cfg_files=[cwd_file]
        assert cae.get_variable(var_name) == cwd_value                  # cwd variable

        usr_file, _, usr_value = config_fna_vna_vva(file_name='{usr}/test' + INI_EXT, var_value='usr')
        assert usr_file != cwd_file
        cae.add_cfg_files()
        cae.load_cfg_files()
        assert cae.get_variable(var_name) == usr_value                       # usr variable overwrite cwd variable

        app_path = normalize("{ado}")   # home/Documents/test will not be removed after test run!
        app_file, _, app_value = config_fna_vna_vva(file_name='{ado}/test' + INI_EXT, var_value='ado')
        assert app_file != cwd_file and app_file != usr_file
        assert app_path.startswith(app_path)
        cae.add_cfg_files()
        cae.load_cfg_files()
        assert cae.get_variable(var_name) == app_value              # usr_app variable overwrites cwd+usr variables

    def test_get_variable_via_cons_app_fixture(self, capsys, cons_app, monkeypatch):
        monkeypatch.setenv("AE_OPTIONS_NAME_OF_VAR", 'value_of_var')

        ret = cons_app.get_variable('name_of_var')

        assert ret == 'value_of_var'
        out, err = capsys.readouterr()
        assert 'AppBase.__init__()' in out
        assert err == ""

    def test_set_option(self, restore_app_env):
        tst_val = 'test_init_value'
        cae = ConsoleApp('test_set_opt')
        cae.add_option('test_opt', 'test_opt_description', tst_val)
        sys.argv = ['tso_pseudo_arg']

        assert cae.get_option('test_opt') == tst_val

        tst_val = 'test_value'
        cae.set_option('test_opt', tst_val, save_to_config=False)

        assert cae.get_option('test_opt') == tst_val

        cae.set_option('debug_level', DEBUG_LEVEL_VERBOSE, save_to_config=False)

        assert cae.get_option('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_set_variable_basics(self, restore_app_env, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(file_name='test' + INI_EXT)

        opt_test_val = 'opt_test_val'
        sys.argv = ['test', '-t=' + opt_test_val]

        cae = ConsoleApp('test_set_variable_basics')
        cae.add_option(var_name, 'test_config_basics', 'init_test_val')
        assert cae.get_option(var_name) == opt_test_val

        val = 'test_value'
        assert not cae.set_variable(var_name, val)
        assert cae.get_variable(var_name) == val

        val = ('test_val1', 'test_val2')
        assert not cae.set_variable(var_name, val)
        assert cae.get_variable(var_name) == repr(val)

        val = datetime.datetime.now()
        assert not cae.set_variable(var_name, val)
        assert cae.get_variable(var_name) == val.strftime(DATE_TIME_ISO)

        val = datetime.date.today()
        assert not cae.set_variable(var_name, val)
        assert cae.get_variable(var_name) == val.strftime(DATE_ISO)

    def test_set_variable_without_ini(self, restore_app_env):
        var_name = 'test_config_var'
        cae = ConsoleApp('test_set_variable_without_ini')
        cae.add_option(var_name, 'test_set_variable_without_ini', 'init_test_val', short_opt='t')
        opt_test_val = 'opt_test_val'
        sys.argv = ['test', '-t=' + opt_test_val]
        assert cae.get_option(var_name) == opt_test_val

        val = 'test_value'
        assert cae.set_variable(var_name, val)        # will be set, but returning error because test.ini does not exist
        assert cae.get_variable(var_name) == val

        val = ('test_val1', 'test_val2')
        assert cae.set_variable(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_variable(var_name) == repr(val)

        val = datetime.datetime.now()
        assert cae.set_variable(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_variable(var_name) == val.strftime(DATE_TIME_ISO)

        val = datetime.date.today()
        assert cae.set_variable(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_variable(var_name) == val.strftime(DATE_ISO)

    def test_set_variable_file_error(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_variable_file_error', additional_cfg_files=[file_name])
        val = 'tt_value'
        assert cae.set_variable(var_name, val, cfg_fnam=os.path.join(os.getcwd(), 'not_existing' + INI_EXT))

    def test_set_variable_while_file_opened(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_variable_while_file_opened', additional_cfg_files=[file_name])
        val = 'tst_value'

        with open(file_name, 'w'):      # although open file set_variable() will not fail
            assert not cae.set_variable(var_name, val, cfg_fnam=file_name)

    def test_set_variable_with_reload(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_variable_with_reload', additional_cfg_files=[file_name])
        val = 'test_value'
        assert not cae.set_variable(var_name, val, cfg_fnam=file_name)

        cfg_val = cae.get_variable(var_name)
        assert cfg_val == val

        cae.load_cfg_files()
        cfg_val = cae.get_variable(var_name)
        assert cfg_val == val

    def test_set_variable_no_option(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_variable_no_option', additional_cfg_files=[file_name])
        val = 'any_test_value'
        section_name = 'tstSection'
        assert not cae.set_variable(var_name, val, cfg_fnam=file_name, section=section_name)

        cfg_val = cae.get_variable(var_name, section=section_name)
        assert cfg_val == val

    def test_set_variable_with_rename(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_variable_with_rename', additional_cfg_files=[file_name])
        val = 'test_value'
        new_var_name = 'new_tst_var_name'
        assert not cae.set_variable(new_var_name, val, cfg_fnam=file_name, old_name=var_name)

        cfg_val = cae.get_variable(var_name)
        assert cfg_val is None
        cfg_val = cae.get_variable(new_var_name)
        assert cfg_val == val

    def test_multiple_option_counted(self, restore_app_env):
        cae = ConsoleApp('test_count_multiple_option')
        sys.argv = ['test', "-C", "-C", "-C"]
        cae.add_option('testCountMultipleOptions', 'test count of multiple option', '++', short_opt='C')
        assert cae.get_option('testCountMultipleOptions') == 3

    def test_multiple_option_counted_default(self, restore_app_env):
        cae = ConsoleApp('test_count_multiple_option')
        sys.argv = ['test']
        cae.add_option('testCountMultipleOptionsDef', 'test default count of multiple option', '++', short_opt='C')

        assert cae.get_option('testCountMultipleOptionsDef') == 0

    def test_multiple_option_counted_fail(self, capsys, restore_app_env):
        cae = ConsoleApp('test_count_multiple_option')
        sys.argv = ['test', "-C=9"]
        cae.add_option('testCountMultipleOptionsFail', 'test default count of multiple option', '++', short_opt='C')

        with pytest.raises(SystemExit):
            _xx = cae.get_option('testCountMultipleOptionsFail')

        out, err = capsys.readouterr()
        assert "ignored explicit argument" in out
        assert "'9'" in out

    def test_multiple_option_single_char(self, restore_app_env):
        cae = ConsoleApp('test_multiple_option')
        sys.argv = ['test', "-Z=a", "-Z=1"]
        cae.add_option('testMultipleOptionSC', 'test multiple option', [], short_opt='Z', multiple=True)

        assert cae.get_option('testMultipleOptionSC') == ['a', '1']

    def test_multiple_option_multi_values(self, restore_app_env):
        cae = ConsoleApp('test_multiple_option_multi_char')
        sys.argv = ['test', "-Z=abc", "-Z=123"]
        cae.add_option('testMultipleOptionMC', 'test multiple option', [], short_opt='Z', multiple=True)

        assert cae.get_option('testMultipleOptionMC') == ['abc', '123']

    def test_multiple_option_multi_values_sep_args(self, restore_app_env):
        cae = ConsoleApp('test_multiple_option_multi_val')
        sys.argv = ['test', "-Z", "abc", '--testMultipleOptionMV', "123"]
        cae.add_option('testMultipleOptionMV', 'test multiple option', [], short_opt='Z', multiple=True)

        assert cae.get_option('testMultipleOptionMV') == ['abc', '123']

    def test_multiple_option_single_char_with_choices(self, restore_app_env):
        cae = ConsoleApp('test_multiple_option_with_choices')
        sys.argv = ['test', "-Z=a", "-Z=1"]
        cae.add_option('testAppOptChoicesSCWC', 'multi choices', [], short_opt='Z', choices=['a', '1'], multiple=True)

        assert cae.get_option('testAppOptChoicesSCWC') == ['a', '1']

    def test_multiple_option_stripped_value_with_choices(self, restore_app_env):
        cae = ConsoleApp('test_multiple_option_stripped_with_choices', cfg_opt_val_stripper=lambda v: v[-1])
        sys.argv = ['test', "-Z=x6", "-Z=yyy9"]
        cae.add_option('testAppOptChoicesSVWC', 'multi choices', [], short_opt='Z', choices=['6', '9'], multiple=True)

        assert cae.get_option('testAppOptChoicesSVWC') == ['x6', 'yyy9']

    def test_multiple_option_single_char_fail_with_invalid_choices(self, capsys, restore_app_env):
        cae = ConsoleApp('test_multiple_option_fail_with_choices')
        sys.argv = ['test', "-Z=x", "-Z=9"]
        cae.add_option('testAppOptChoicesInv', 'multiple choices', [], short_opt='Z', choices=['a', '1'], multiple=True)

        with pytest.raises(SystemExit):
            cae.get_option('testAppOptChoicesInv')     # == ['x', '9'] but choices is ['a', '1']

        out, err = capsys.readouterr()
        assert 'testAppOptChoicesInv' in out
        assert "given_value='x'" in out
        assert "'a', '1'" in out

    def test_config_default_bool(self, restore_app_env):
        cae = ConsoleApp('test_config_defaults')
        cfg_val = cae.get_variable('not_existing_config_var', default_value=False)
        assert cfg_val is False

        cfg_val = cae.get_variable('not_existing_config_var2', value_type=bool)

        assert cfg_val is False

    def test_long_option_str_value(self, restore_app_env):
        cae = ConsoleApp('test_long_option_str_value')
        opt_val = 'testString'
        sys.argv = ['test', '--testStringOption=' + opt_val]
        cae.add_option('testStringOption', 'test long option', '', short_opt='Z')

        assert cae.get_option('testStringOption') == opt_val

    def test_short_option_str_value(self, restore_app_env):
        cae = ConsoleApp('test_option_str_value')
        opt_val = 'testString'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testStringOption', 'test short option', '', short_opt='Z')

        assert cae.get_option('testStringOption') == opt_val

    def test_short_option_str_eval(self, restore_app_env):
        cae = ConsoleApp('test_option_str_eval')
        opt_val = 'testString'
        sys.argv = ['test', '-Z=""""' + opt_val + '""""']
        cae.add_option('testString2Option', 'test str eval short option', '', short_opt='Z')

        assert cae.get_option('testString2Option') == opt_val

    def test_short_option_bool_str(self, restore_app_env):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = 'False'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool str option', True, short_opt='Z')

        assert cae.get_option('testBoolOption') is False

    def test_short_option_bool_number(self, restore_app_env):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '0'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool number option', True, short_opt='Z')

        assert cae.get_option('testBoolOption') is False

    def test_short_option_bool_number_true(self, restore_app_env):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '1'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool number option', False, short_opt='Z')

        assert cae.get_option('testBoolOption') is True

    def test_short_option_bool_eval(self, restore_app_env):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '"""0 == 1"""'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool eval option', True, short_opt='Z')

        assert cae.get_option('testBoolOption') is False

    def test_short_option_bool_eval_true(self, restore_app_env):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '"""9 == 9"""'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testBoolOption', 'test bool eval option', False, short_opt='Z')

        assert cae.get_option('testBoolOption') is True

    def test_short_option_bool_flag(self, restore_app_env):
        cae = ConsoleApp('test_option_bool_flag')
        sys.argv = ['test', '-Z']
        cae.add_option('testBoolFlagOption', 'test bool flag option', UNSET, short_opt='Z')

        assert cae.get_option('testBoolFlagOption') is True

    def test_short_option_date_str(self, restore_app_env):
        cae = ConsoleApp('test_option_date_str')
        opt_val = '2016-12-24'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testDateOption', 'test date str option', datetime.date.today(), short_opt='Z')

        assert cae.get_option('testDateOption') == datetime.date(year=2016, month=12, day=24)

    def test_short_option_datetime_str(self, restore_app_env):
        cae = ConsoleApp('test_option_datetime_str')
        opt_val = '2016-12-24 7:8:0.0'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_option('testDatetimeOption', 'test datetime str option', datetime.datetime.now(), short_opt='Z')

        assert cae.get_option('testDatetimeOption') == datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)

    def test_short_option_date_eval(self, restore_app_env):
        cae = ConsoleApp('test_option_date_eval')
        sys.argv = ['test', '-Z="""datetime.date(year=2016, month=12, day=24)"""']
        cae.add_option('testDateOption', 'test date eval test option', datetime.date.today(), short_opt='Z')

        assert cae.get_option('testDateOption') == datetime.date(year=2016, month=12, day=24)

    def test_short_option_datetime_eval(self, restore_app_env):
        cae = ConsoleApp('test_option_datetime_eval')
        sys.argv = ['test', '-Z="""datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)"""']
        cae.add_option('testDatetimeOption', 'test datetime eval test option', datetime.datetime.now(), short_opt='Z')

        assert cae.get_option('testDatetimeOption') == datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)

    def test_short_option_list_str(self, restore_app_env):
        cae = ConsoleApp('test_option_list_str')
        opt_val = [1, 2, 3]
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_option('testListStrOption', 'test list str option', [], short_opt='Z')

        assert cae.get_option('testListStrOption') == opt_val

    def test_short_option_list_eval(self, restore_app_env):
        cae = ConsoleApp('test_option_list_eval')
        sys.argv = ['test', '-Z="""[1, 2, 3]"""']
        cae.add_option('testListEvalOption', 'test list eval option', [], short_opt='Z')

        assert cae.get_option('testListEvalOption') == [1, 2, 3]

    def test_short_option_dict_str(self, restore_app_env):
        cae = ConsoleApp('test_option_dict_str')
        opt_val = {'a': 1, 'b': 2, 'c': 3}
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_option('testDictStrOption', 'test list str option', {}, short_opt='Z')

        assert cae.get_option('testDictStrOption') == opt_val

    def test_short_option_dict_eval(self, restore_app_env):
        cae = ConsoleApp('test_option_dict_eval')
        sys.argv = ['test', "-Z='''{'a': 1, 'b': 2, 'c': 3}'''"]
        cae.add_option('testDictEvalOption', 'test dict eval option', {}, short_opt='Z')

        assert cae.get_option('testDictEvalOption') == {'a': 1, 'b': 2, 'c': 3}

    def test_short_option_tuple_str(self, restore_app_env):
        cae = ConsoleApp('test_option_tuple_str')
        opt_val = ('a', 'b', 'c')
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_option('testTupleStrOption', 'test tuple str option', (), short_opt='Z')

        assert cae.get_option('testTupleStrOption') == opt_val

    def test_short_option_tuple_eval(self, restore_app_env):
        cae = ConsoleApp('test_option_tuple_eval')
        sys.argv = ['test', "-Z='''('a', 'b', 'c')'''"]
        cae.add_option('testDictEvalOption', 'test tuple eval option', (), short_opt='Z')

        assert cae.get_option('testDictEvalOption') == ('a', 'b', 'c')

    def test_config_str_eval_single_quote(self, config_fna_vna_vva, restore_app_env):
        opt_val = 'testString'
        file_name, var_name, _ = config_fna_vna_vva(var_value="''''" + opt_val + "''''")
        cae = ConsoleApp('test_config_str_eval', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) == opt_val

    def test_config_str_eval_double_quote(self, config_fna_vna_vva, restore_app_env):
        opt_val = 'testString'
        file_name, var_name, _ = config_fna_vna_vva(var_value='""""' + opt_val + '""""')
        cae = ConsoleApp('test_config_str_eval', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) == opt_val

    def test_config_bool_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='True')
        cae = ConsoleApp('test_config_bool_str', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name, value_type=bool) is True

    def test_config_bool_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""1 == 0"""')
        cae = ConsoleApp('test_config_bool_eval', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) is False

    def test_config_bool_eval_true(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""6 == 6"""')
        cae = ConsoleApp('test_config_bool_eval', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) is True

    def test_config_date_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='2012-12-24')
        cae = ConsoleApp('test_config_date_str', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name, value_type=datetime.date) == datetime.date(year=2012, month=12, day=24)

    def test_config_date_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""datetime.date(year=2012, month=12, day=24)"""')
        cae = ConsoleApp('test_config_date_str', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) == datetime.date(year=2012, month=12, day=24)

    def test_config_datetime_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='2012-12-24 7:8:0.0')
        cae = ConsoleApp('test_config_date_str', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name, value_type=datetime.datetime) \
            == datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)

    def test_config_datetime_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(
            var_value='"""datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)"""')
        cae = ConsoleApp('test_config_datetime_eval', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) == datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)

    def test_config_list_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='[1, 2, 3]')
        cae = ConsoleApp('test_config_list_str', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) == [1, 2, 3]

    def test_config_list_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""[1, 2, 3]"""')
        cae = ConsoleApp('test_config_list_eval', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) == [1, 2, 3]

    def test_config_dict_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value="{'a': 1, 'b': 2, 'c': 3}")
        cae = ConsoleApp('test_config_dict_str', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) == {'a': 1, 'b': 2, 'c': 3}

    def test_config_dict_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""{"a": 1, "b": 2, "c": 3}"""')
        cae = ConsoleApp('test_config_dict_eval', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) == {'a': 1, 'b': 2, 'c': 3}

    def test_config_tuple_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value="('a', 'b', 'c')")
        cae = ConsoleApp('test_config_tuple_str', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) == ('a', 'b', 'c')

    def test_config_tuple_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""("a", "b", "c")"""')
        cae = ConsoleApp('test_config_tuple_eval', additional_cfg_files=[file_name])

        assert cae.get_variable(var_name) == ('a', 'b', 'c')

    def test_base_debug_level_add_opt_default(self, restore_app_env):
        cae = ConsoleApp('test_add_opt_default')

        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_short_option_value(self, restore_app_env):
        cae = ConsoleApp('test_option_value')
        sys.argv = ['test', '-D=' + str(DEBUG_LEVEL_VERBOSE)]
        cae.run_app()

        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_long_option_value(self, restore_app_env):
        cae = ConsoleApp('test_long_option_value')
        sys.argv = ['test', '--debug_level=' + str(DEBUG_LEVEL_VERBOSE)]
        cae.run_app()

        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_short_option_eval_single_quoted(self, restore_app_env):
        cae = ConsoleApp('test_quoted_option_eval')
        sys.argv = ["test", "-D='''int('" + str(DEBUG_LEVEL_VERBOSE) + "')'''"]
        cae.run_app()

        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_short_option_eval_double_quoted(self, restore_app_env):
        cae = ConsoleApp('test_double_quoted_option_eval')
        sys.argv = ['test', '-D="""int("' + str(DEBUG_LEVEL_VERBOSE) + '")"""']
        cae.run_app()

        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_config_default(self, restore_app_env, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debug_level', var_value=str(DEBUG_LEVEL_VERBOSE))
        cae = ConsoleApp('test_config_default', additional_cfg_files=[file_name])
        sys.argv = [restore_app_env, ]
        cae.run_app()

        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_config_eval_single_quote(self, restore_app_env, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debug_level',
                                                    var_value="'''int('" + str(DEBUG_LEVEL_VERBOSE) + "')'''")
        cae = ConsoleApp('test_config_eval', additional_cfg_files=[file_name])
        sys.argv = [restore_app_env, ]
        cae.run_app()

        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_debug_level_short_option_value(self, restore_app_env):
        cae = ConsoleApp('test_option_value')
        sys.argv = ['test', '-D=' + str(DEBUG_LEVEL_VERBOSE)]

        assert cae.get_option('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_debug_level_long_option_value(self, restore_app_env):
        cae = ConsoleApp('test_long_option_value')
        sys.argv = ['test', '--debug_level=' + str(DEBUG_LEVEL_VERBOSE)]

        assert cae.get_option('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_debug_level_short_option_eval_single_quoted(self, restore_app_env):
        cae = ConsoleApp('test_quoted_option_eval')
        sys.argv = ["test", "-D='''int('" + str(DEBUG_LEVEL_VERBOSE) + "')'''"]

        assert cae.get_option('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_debug_level_short_option_eval_double_quoted(self, restore_app_env):
        cae = ConsoleApp('test_double_quoted_option_eval')
        sys.argv = ['test', '-D="""int("' + str(DEBUG_LEVEL_VERBOSE) + '")"""']

        assert cae.get_option('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_debug_level_config_default(self, restore_app_env, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debug_level', var_value=str(DEBUG_LEVEL_VERBOSE))
        cae = ConsoleApp('test_config_default', additional_cfg_files=[file_name])
        sys.argv = [restore_app_env, ]

        assert cae.get_option(var_name) == DEBUG_LEVEL_VERBOSE

    def test_debug_level_config_eval_single_quote(self, restore_app_env, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debug_level',
                                                    var_value="'''int('" + str(DEBUG_LEVEL_VERBOSE) + "')'''")
        cae = ConsoleApp('test_config_eval', additional_cfg_files=[file_name])
        sys.argv = [restore_app_env, ]

        assert cae.get_option(var_name) == DEBUG_LEVEL_VERBOSE

    def test_debug_level_config_eval_double_quote(self, restore_app_env, config_fna_vna_vva):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debug_level',
                                                    var_value='"""int("' + str(DEBUG_LEVEL_VERBOSE) + '")"""')
        cae = ConsoleApp('test_config_double_eval', additional_cfg_files=[file_name])
        sys.argv = [restore_app_env, ]

        assert cae.get_option(var_name) == DEBUG_LEVEL_VERBOSE

    def test_sys_env_id_with_debug(self, restore_app_env):
        cae = ConsoleApp('test_sys_env_id_with_debug', sys_env_id='OTHER')
        sys.argv = ['test', '-D=' + str(DEBUG_LEVEL_VERBOSE)]

        assert cae.get_option('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_config_main_file_not_modified(self, config_fna_vna_vva, restore_app_env):
        config_fna_vna_vva(
            file_name=os.path.join(os.getcwd(), os.path.splitext(os.path.basename(sys.argv[0]))[0] + INI_EXT))
        cae = ConsoleApp('test_config_modified_after_startup')

        assert not cae.is_main_cfg_file_modified()

    def test_is_main_cfg_file_modified(self, config_fna_vna_vva, restore_app_env):
        app_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
        file_name, var_name, old_var_val = config_fna_vna_vva(file_name=os.path.join(os.getcwd(), app_name + INI_EXT))

        cae = ConsoleApp('test_set_var_with_reload', app_name=app_name)  # not needed: additional_cfg_files=[file_name]
        time.sleep(.963)    # needed because Python is too quick, especially on github-ci (fails sometimes with 0.639)
        new_var_val = 'NEW_test_value'

        assert not cae.set_variable(var_name, new_var_val)
        assert cae.is_main_cfg_file_modified()

        # cfg_val has already new value (NEW_test_value) because parser instance got reloaded
        cfg_val = cae.get_variable(var_name)

        assert cfg_val != old_var_val
        assert cfg_val == new_var_val
        assert cae.is_main_cfg_file_modified()

        cae.load_cfg_files()

        cfg_val = cae.get_variable(var_name)

        assert cfg_val == new_var_val
        assert not cae.is_main_cfg_file_modified()

    def test_cfg_section_variable_names(self, restore_app_env, config_fna_vna_vva):
        file_name, var_name, _old_var_val = config_fna_vna_vva()
        cae = ConsoleApp(additional_cfg_files=[file_name])
        var_names = cae.cfg_section_variable_names(MAIN_SECTION_NAME)

        assert var_name in var_names

    def test_cfg_section_variable_names_missing_section(self, restore_app_env, config_fna_vna_vva):
        _file_name, _var_name, _old_var_val = config_fna_vna_vva()
        cae = ConsoleApp()
        var_names = cae.cfg_section_variable_names("missing_section_name")

        assert not var_names
        assert isinstance(var_names, tuple)

    def test_app_instances_reset2(self):
        assert main_app_instance() is None


class TestConsoleAppBasics:
    def test_app_instance_of_cons_app_fixture(self, cons_app):
        assert isinstance(cons_app, ConsoleApp)
        # main_app = main_app_instance()   -->  FAILS - returns None ?!?!?
        # assert isinstance(main_app, ConsoleApp)
        # assert main_app is cons_app

        assert cons_app.debug is True
        assert cons_app.verbose is True

        assert callable(cons_app.chk)
        assert callable(cons_app.po)
        assert callable(cons_app.dpo)
        assert callable(cons_app.vpo)
        assert callable(cons_app.get_option)
        assert callable(cons_app.get_argument)
        assert callable(cons_app.get_variable)
        assert callable(cons_app.set_option)
        assert callable(cons_app.set_variable)
        assert callable(cons_app.show_help)
        assert callable(cons_app.shutdown)

    def test_app_instances_reset0(self):
        assert main_app_instance() is None

    def test_app_name(self, restore_app_env):
        assert main_app_instance() is None
        name = 'tan_cae_name'
        sys.argv = [name, ]
        cae = ConsoleApp()

        assert cae.app_name == name
        assert main_app_instance() is cae

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_debug_level_set_property(self, restore_app_env):
        cae = ConsoleApp()

        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

        cae.debug_level = DEBUG_LEVEL_DISABLED

        assert cae.debug_level == DEBUG_LEVEL_DISABLED

    def test_show_help(self, capsys, restore_app_env):
        cae = ConsoleApp('tst_show_help')
        
        cae.show_help()

        out, err = capsys.readouterr()
        assert err == ""
        assert out
        # pjm check fails (not PyCharm) with file arg in show_help(): self._arg_parser.print_help(file=ori_std_out)?!?!?
        assert 'tst_show_help' in out
        assert 'pyTstConsAppKey' in out

    def test_show_help_via_cons_app_fixture(self, capsys, cons_app):
        cons_app.show_help()

        out, err = capsys.readouterr()
        assert err == ""
        assert out
        assert 'pyTstConsAppKey' in out

    def test_app_instances_reset3(self):
        from ae.core import _APP_INSTANCES
        assert main_app_instance() is None
        assert not _APP_INSTANCES

    def test_show_parse_error_and_exit(self, capsys, restore_app_env):
        from ae.core import _APP_INSTANCES  # temp. debugging info - sometimes show_help() does not output ?!?!?
        print(f"\n\n\n______ PRE {main_app_instance()=} {list(_APP_INSTANCES.items())}")
        main_app = ConsoleApp('test_show_parse_error_and_exit')
        print(f"\n\n\n______ POS {main_app_instance()=} {list(_APP_INSTANCES.items())}")

        message = 'any message to be shown at the end of the show help console output'

        with pytest.raises(SystemExit) as ex:
            main_app.show_parse_error_and_exit(message)

        assert ex.value.code == 255
        out, err = capsys.readouterr()
        assert message in out
        # assert 'test_show_parse_error_and_exit' in out  # displayed by show_help() - failing sometimes ?!?!?

    def test_sys_env_id(self, capsys, restore_app_env):
        sei = 'tSt'
        cae = ConsoleApp('test_sys_env_id', sys_env_id=sei)

        assert cae.sys_env_id == sei

        cae.po(sei)     # increase coverage

        out, err = capsys.readouterr()
        assert sei in out

        # special case for error code path coverage
        ca2 = ConsoleApp('test_sys_env_id_COPY', debug_level=DEBUG_LEVEL_DISABLED)

        assert ca2.sys_env_id == ''
        assert not ca2.get_option('debug_level')

    def test_chk_no_shutdown(self, capsys, cons_app, restore_app_env):
        cons_app.chk(-69, True, 'unused error message')     # no shutdown() call because 2nd arg (check_result) is True

        out, err = capsys.readouterr()
        assert 'unused error message' not in out
        assert 'unused error message' not in err

    def test_chk_no_shutdown_with_force(self, cons_app, restore_app_env):
        with patch('ae.console.ConsoleApp.get_option', return_value=1):
            # no shutdown() call because 'force' app option got patched to be 1/True
            cons_app.chk(-99, False, "error message printed to console")

    def test_chk_shutdown(self, cons_app, restore_app_env):
        def _shutdown(_self, **kwargs):     # app.shutdown() args: 1st==self, 2nd==error code, 3rd==error message
            _shutdown_args.append(kwargs)
        _shutdown_args = []
        err_msg = "error message passed onto shutdown()"

        with patch('ae.core.AppBase.shutdown', new=_shutdown):
            cons_app.chk(963, False, err_msg)

        assert len(_shutdown_args) >= 1  # if runs via pjm check then 2 more shutdown calls with default arg values?!?!?
        assert _shutdown_args[-1]['exit_code'] == 963
        assert _shutdown_args[-1]['error_message'].startswith(err_msg)

        with patch('ae.console.ConsoleApp.shutdown', new=_shutdown):
            cons_app.chk(969, False, err_msg)

        assert len(_shutdown_args) >= 2
        assert _shutdown_args[-1]['exit_code'] == 969
        assert _shutdown_args[-1]['error_message'].startswith(err_msg)

    def test_shutdown_basics(self, restore_app_env):
        def thr():
            """ thread """
            while running:
                pass

        cae = ConsoleApp('shutdown_basics')
        cae.shutdown(exit_code=None)
        cae._got_shut_down = False

        try:
            activate_multi_threading()

            cae.shutdown(exit_code=None, timeout=0.6)       # tests freezing in debug run without timeout/thread-join
            cae._got_shut_down = False

            running = True
            threading.Thread(target=thr).start()
            cae.shutdown(exit_code=None, timeout=0.6)

        finally:
            running = False
            _deactivate_multi_threading()

    def test_shutdown_calling_show_help(self, cons_app):
        po_calls_args = []

        def _po(*args, **_kwargs):
            nonlocal po_calls_args
            po_calls_args.append(args)

        cons_app.po = _po

        sh_called = 0

        def _sh():
            nonlocal sh_called
            sh_called += 1

        cons_app.show_help = _sh

        ex_args = ()

        def _ex(*args):
            nonlocal ex_args
            ex_args = args

        cons_app.po = _po

        with patch('sys.exit', new=_ex):
            cons_app.shutdown(3, error_message='err3')

        assert len(po_calls_args) == 2
        assert po_calls_args[0][0] == '***** ' + 'err3'
        assert po_calls_args[1][0].startswith('##### forced shutdown')
        assert po_calls_args[1][0].endswith('exit_code=3')
        assert sh_called == 1
        assert ex_args == (3, )

    def test_app_instances_reset2(self):
        assert main_app_instance() is None


class TestUser:
    def test_load_user_cfg_user_id_from_os(self, restore_app_env, config_fna_vna_vva):
        _file_name, _var_name, _old_var_val = config_fna_vna_vva()
        cae = ConsoleApp()

        assert cae.user_id == os_user_name()

        changed_user = 'chg_usr'
        cae.user_id = ''

        with patch('ae.console.os_user_name', lambda: changed_user):
            cae.load_user_cfg()

        assert cae.user_id == changed_user

    def test_load_user_cfg_user_id_from_cfg_var(self, restore_app_env, config_fna_vna_vva):
        file_name, _var_name, var_val = config_fna_vna_vva(var_name='user_id')
        cae = ConsoleApp(additional_cfg_files=(file_name, ))

        assert cae.user_id == var_val

        cae.user_id = ''

        cae.load_user_cfg()

        assert cae.user_id == var_val

    def test_load_user_cfg_user_id_from_cfg_opt_default(self, restore_app_env):
        def_val = "option_default_value"
        cae = ConsoleApp()
        cae.add_option('user_id', "user id test", def_val)
        cae.parse_arguments()

        assert cae.user_id == def_val

        cae.load_user_cfg()

        assert cae.user_id == def_val

    def test_load_user_cfg_user_id_from_cfg_opt_preference(self, restore_app_env, config_fna_vna_vva):
        file_name, _var_name, var_val = config_fna_vna_vva(var_name='user_id')
        def_val = "option_default_value"
        opt_val = "option_value"

        assert var_val != def_val != opt_val

        sys.argv = ['test', f"--user_id={opt_val}"]
        cae = ConsoleApp(additional_cfg_files=(file_name, ))
        cae.add_option('user_id', "user id test", def_val)

        assert cae.get_option('user_id') == opt_val  # or call cae.run_app() instead of get_option() to parse args/opts

        assert cae.user_id == opt_val

        cae.user_id = ''

        cae.load_user_cfg()                         # .. and cae.load_user_cfg() to reload user id (see next test)

        assert cae.user_id == opt_val

    def test_load_user_cfg_user_id_from_cfg_opt_preference_with_run_app(self, restore_app_env, config_fna_vna_vva):
        file_name, _var_name, var_val = config_fna_vna_vva(var_name='user_id')
        def_val = "option_default_value"
        opt_val = "option_value"

        assert var_val != def_val != opt_val

        cae = ConsoleApp(additional_cfg_files=(file_name, ))
        sys.argv = ['test', f"--user_id={opt_val}"]
        cae.add_option('user_id', "user id test", def_val)

        cae.run_app()

        assert cae.user_id == opt_val

    def test_load_user_cfg_registered_users_not_configured(self, restore_app_env):
        cae = ConsoleApp()

        assert not cae.registered_users

        assert isinstance(cae.registered_users, list)

        cae.load_user_cfg()

        assert not cae.registered_users
        assert isinstance(cae.registered_users, list)

    def test_load_user_cfg_registered_users_from_cfg(self, restore_app_env, config_fna_vna_vva):
        reg_users = ['user_ai_di']
        file_name, _var_name, var_val = config_fna_vna_vva(var_name='registered_users', var_value=repr(reg_users))
        cae = ConsoleApp(additional_cfg_files=(file_name, ))

        cae.load_user_cfg()

        assert cae.registered_users == reg_users

    def test_load_user_cfg_user_specific_cfg_vars_not_configured(self, restore_app_env):
        cae = ConsoleApp()

        assert cae.user_specific_cfg_vars
        assert isinstance(cae.user_specific_cfg_vars, set)

        cae.load_user_cfg()

        assert cae.user_specific_cfg_vars
        assert isinstance(cae.user_specific_cfg_vars, set)

    def test_load_user_cfg_user_specific_cfg_vars_users_from_cfg(self, restore_app_env, config_fna_vna_vva):
        usr_vars = {(MAIN_SECTION_NAME, 'tst_var')}
        file_name, _var_name, var_val = config_fna_vna_vva(var_name='user_specific_cfg_vars', var_value=repr(usr_vars),
                                                           additional_line=f"registered_users = {dict(usr={})!r}")
        cae = ConsoleApp(additional_cfg_files=(file_name, ))

        cae.load_user_cfg()

        assert cae.user_specific_cfg_vars == usr_vars

    def test_load_user_cfg_users_registered(self, restore_app_env, config_fna_vna_vva):
        reg_users = ['usr_id']
        file_name, _var_name, var_val = config_fna_vna_vva(additional_line=f"registered_users = {reg_users!r}")
        cae = ConsoleApp(additional_cfg_files=(file_name, ))

        assert len(cae.registered_users) == 1

        cae.load_user_cfg()

        assert len(cae.registered_users) == 1
        assert cae.registered_users == reg_users

    def test_register_user(self, restore_app_env, config_fna_vna_vva):
        usr_var_name = 'tst_usr_var'
        usr_var_val = 'tst_usr_var_val'
        usr_vars = {(MAIN_SECTION_NAME, usr_var_name)}
        file_name, _var_name, var_val = config_fna_vna_vva(var_name='user_specific_cfg_vars', var_value=repr(usr_vars),
                                                           additional_line=f"{usr_var_name} = {usr_var_val!r}")
        cae = ConsoleApp(additional_cfg_files=[file_name])

        assert cae._main_cfg_fnam == file_name

        cae._cfg_files.append(file_name)
        cae.load_cfg_files()
        cae.load_user_cfg()     # load cfg/usr manually: therefore no ConsoleApp(additional_cfg_files=(file_name, ))

        os_usr_id = cae.user_id
        new_usr_id = 'new_usr_id'

        assert isinstance(cae.registered_users, list)
        assert len(cae.registered_users) == 0
        assert cae.user_id == os_usr_id

        cae.user_id = new_usr_id
        assert cae.get_variable(usr_var_name) == usr_var_val
        cae.user_id = os_usr_id
        assert cae.get_variable(usr_var_name) == usr_var_val

        cae.register_user()     # == cae.register_user(new_user_id=os_usr_id, set_as_default=True)

        assert len(cae.registered_users) == 1
        assert os_usr_id in cae.registered_users
        assert cae.user_id == os_usr_id

        cae.user_id = new_usr_id
        assert cae.get_variable(usr_var_name) == usr_var_val
        cae.user_id = os_usr_id
        assert cae.get_variable(usr_var_name) == usr_var_val

        os_usr_chg_val = 'os_usr_chg_val'
        cae.set_variable(usr_var_name, os_usr_chg_val, cfg_fnam=file_name)

        cae.user_id = new_usr_id
        assert cae.get_variable(usr_var_name) == usr_var_val
        cae.user_id = os_usr_id
        assert cae.get_variable(usr_var_name) == os_usr_chg_val

        # test user data on re-registration get untouched
        cae.register_user(new_user_id=os_usr_id)
        assert cae.get_variable(usr_var_name) == os_usr_chg_val
        assert len(cae.registered_users) == 1
        assert os_usr_id in cae.registered_users
        # .. until reset_cfg_vars get specified
        cae.register_user(new_user_id=os_usr_id, reset_cfg_vars=True)
        assert cae.get_variable(usr_var_name) == usr_var_val

        cae.register_user(new_user_id=new_usr_id, set_as_default=False)
        assert len(cae.registered_users) == 2
        assert new_usr_id in cae.registered_users
        assert cae.user_id == os_usr_id

        cae.register_user(new_user_id=new_usr_id)
        assert len(cae.registered_users) == 2
        assert new_usr_id in cae.registered_users
        assert cae.user_id == new_usr_id

    def test_register_user_empty_or_invalid_id(self, restore_app_env):
        cae = ConsoleApp()

        with pytest.raises(AssertionError):
            cae.register_user(new_user_id="x y")
        with pytest.raises(AssertionError):
            cae.register_user(new_user_id="x-y")
        with pytest.raises(AssertionError):
            cae.register_user(new_user_id="xy=")
        with pytest.raises(AssertionError):
            cae.register_user(new_user_id="(xy")
        with pytest.raises(AssertionError):
            cae.register_user(new_user_id="x" * (USER_NAME_MAX_LEN + 1))

        cae.register_user(new_user_id="x_y")    # only underscore is allowed in user id

    def test_set_user_id(self, restore_app_env):
        cae = ConsoleApp()
        usr_id = 'usr id with spaces'
        assert norm_name(usr_id) != usr_id
        cae.user_id = usr_id
        assert cae.user_id != usr_id
        assert cae.user_id == norm_name(usr_id)

    def test_user_section(self, restore_app_env):
        usr_id = 'usr_tst_id'
        cae = ConsoleApp()
        cae.user_id = usr_id
        cae.registered_users = [usr_id]
        cae.user_specific_cfg_vars = {('section', 'var_nam')}

        assert cae.user_section('xxx', 'var_nam') == 'xxx'
        assert cae.user_section('section', 'yyy_var_nam') == 'section'
        assert cae.user_section('section', 'var_nam') == 'section' + '_usr_id_' + usr_id
        assert cae.user_section('section') == 'section' + '_usr_id_' + usr_id
