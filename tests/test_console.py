""" ae_console unit tests. """
import datetime
import logging
import os
import sys
import threading
import time

from argparse import ArgumentError
from typing import cast, Any

import pytest
from conftest import delete_files

from ae.base import DATE_ISO, DATE_TIME_ISO
from ae.paths import norm_path
from ae.core import (DEBUG_LEVEL_DISABLED, DEBUG_LEVEL_VERBOSE, MAX_NUM_LOG_FILES,
                     activate_multi_threading, main_app_instance, po, SubApp)
from ae.console import INI_EXT, MAIN_SECTION_NAME, ConsoleApp


@pytest.fixture
def config_fna_vna_vva(request):
    """ prepare config test files """
    def _setup_and_teardown(file_name='test_config.cfg', var_name='test_config_var', var_value: Any = 'test_value'):
        file_name = norm_path(file_name)
        if os.path.sep not in file_name:
            file_name = os.path.join(os.getcwd(), file_name)
        with open(file_name, 'w') as f:
            f.write(f"[{MAIN_SECTION_NAME}]\n{var_name} = {var_value}")

        def _tear_down():               # using yield instead of finalizer does not execute the teardown part
            if os.path.exists(file_name):       # some tests are deleting the config file explicitly
                os.remove(file_name)
        request.addfinalizer(_tear_down)

        return file_name, var_name, var_value

    return _setup_and_teardown


class TestAeLogging:
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

    def test_cae_log_file_rotation(self, restore_app_env, sys_argv_app_key_restore):
        log_file = 'test_cae_rot_log.log'
        cae = ConsoleApp('test_cae_log_file_rotation',
                         multi_threading=True, log_file_name=log_file, log_file_size_max=.001)
        try:
            sys.argv = [sys_argv_app_key_restore, ]
            file_name_chk = cae.get_opt('log_file')   # get_opt() has to be called at least once for to create log file
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

        cae = ConsoleApp('test_ae_logging_params_dict_from_ini', additional_cfg_files=[file_name])
        cfg_val = cae.get_var(var_name)
        try:
            assert cfg_val == var_val
            assert cae.get_var(var_name) == var_val
            assert cae._log_file_name == cfg_val['log_file_name']
            assert not os.path.exists(cfg_val['log_file_name'])

            cae.po(log_msg)
            assert os.path.exists(cfg_val['log_file_name'])

            logging.shutdown()
        finally:
            assert delete_files(cfg_val['log_file_name'], ret_type="contents") == ["\n" + log_msg]

    def test_app_instances_reset2(self):
        assert main_app_instance() is None

    def test_app_instances_reset3(self):
        assert main_app_instance() is None

    def test_log_file_flush(self, restore_app_env, sys_argv_app_key_restore):
        log_file = 'test_ae_log_flush.log'
        cae = ConsoleApp('test_log_file_flush', log_file_name=log_file)
        try:
            sys.argv = [sys_argv_app_key_restore, ]
            file_name_chk = cae.get_opt('log_file')   # get_opt() has to be called at least once for to create log file
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
            app = ConsoleApp('test_main_app')
            app.init_logging(log_file_name=mp + log_file)
            sub = SubApp('test_sub_app', app_name=sp)
            sub.init_logging(log_file_name=sp + log_file)
            po(mp + tst_out + "_1")
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
            assert mp + tst_out + "_1" in contents[0]
            assert mp + tst_out + "_2" in contents[0]
            assert sp + tst_out not in contents[0]

    def test_threaded_sub_app_logging(self, restore_app_env):
        sub_printed = False

        def sub_app_po():
            """ sub app thread function """
            nonlocal sub, sub_printed
            sub = SubApp('test_sub_app_thread', app_name=sp)
            sub.init_logging(log_file_name=sp + log_file)
            sub.po(sp + tst_out)
            sub_printed = True

        log_file = 'test_threaded_sub_app_logging.log'
        tst_out = 'print-out to log file'
        mp = "MAIN_"  # main/sub-app prefixes for log file names and print-outs
        sp = "SUB__"
        try:
            app = ConsoleApp('test_main_app_thread', app_name=mp, multi_threading=True)
            app.init_logging(log_file_name=mp + log_file)
            sub = None
            sub_thread = threading.Thread(target=sub_app_po)
            sub_thread.start()
            while not sub_printed:      # NOT ENOUGH - failing on gitlab ci with: not sub or not sub.active_log_stream:
                pass  # wait until sub-thread has called init_logging()
            po(mp + tst_out + "_1")
            app.po(mp + tst_out + "_2")
            assert isinstance(sub, SubApp)
            sub.init_logging()  # close sub-app log file
            sub_thread.join()
            app.init_logging()  # close main-app log file
            assert os.path.exists(sp + log_file)
            assert os.path.exists(mp + log_file)
        finally:
            contents = delete_files(mp + log_file, ret_type='contents')
            assert len(contents)
            assert mp + tst_out + "_1" in contents[0]
            assert mp + tst_out + "_2" in contents[0]
            assert sp + tst_out not in contents[0]
            contents = delete_files(sp + log_file, ret_type='contents')
            assert len(contents)
            assert mp + tst_out + "_1" in contents[0]
            assert mp + tst_out + "_2" in contents[0]
            assert sp + tst_out in contents[0]

    def test_exception_log_file_flush(self, restore_app_env):
        cae = ConsoleApp('test_exception_log_file_flush')
        # cause/provoke _append_eof_and_flush_file() exceptions for coverage by passing any other non-stream object
        cae._append_eof_and_flush_file(cast('TextIO', None), 'invalid stream')

    def test_app_instances_reset_fin(self):
        assert main_app_instance() is None


class TestPythonLogging:
    """ test python logging module support
    """
    def test_logging_params_dict_basic_from_cfg(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, var_val = config_fna_vna_vva(var_name='py_logging_params',
                                                          var_value=dict(version=1,
                                                                         disable_existing_loggers=False))

        cae = ConsoleApp('test_python_logging_params_dict_basic_from_ini', additional_cfg_files=[file_name])

        cfg_val = cae.get_var(var_name)
        assert cfg_val == var_val

        assert cae.py_log_params == var_val

        logging.shutdown()

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_logging_params_dict_console_from_init(self, restore_app_env):
        var_val = dict(version=1,
                       disable_existing_loggers=False,
                       handlers=dict(console={'class': 'logging.StreamHandler',
                                              'level': logging.INFO}))
        print(str(var_val))

        cae = ConsoleApp('test_python_logging_params_dict_console', py_logging_params=var_val)

        assert cae.py_log_params == var_val
        logging.shutdown()

    def test_logging_params_dict_complex(self, caplog, restore_app_env, sys_argv_app_key_restore):
        log_file = 'test_py_log_complex.log'
        entry_prefix = "TEST LOG ENTRY "

        var_val = dict(version=1,
                       disable_existing_loggers=False,
                       handlers=dict(console={'class': 'logging.handlers.RotatingFileHandler',
                                              'level': logging.INFO,
                                              'filename': log_file,
                                              'maxBytes': 33,
                                              'backupCount': 63}),
                       loggers={'root': dict(handlers=['console']),
                                'ae': dict(handlers=['console']),
                                'ae.console': dict(handlers=['console'])}
                       )
        print(str(var_val))

        cae = ConsoleApp('test_python_logging_params_dict_file', py_logging_params=var_val)

        assert cae.py_log_params == var_val

        root_logger = logging.getLogger()
        ae_logger = logging.getLogger('ae')
        ae_cae_logger = logging.getLogger('ae.console')

        # ConsoleApp print_out
        log_text = entry_prefix + "0 print_out"
        cae.po(log_text)
        assert caplog.text == ""

        log_text = entry_prefix + "0 print_out root"
        cae.po(log_text, logger=root_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 print_out ae"
        cae.po(log_text, logger=ae_logger)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "0 print_out ae_cae"
        cae.po(log_text, logger=ae_cae_logger)
        assert caplog.text.endswith(log_text + "\n")

        # logging
        logging.info(entry_prefix + "1 info")       # will NOT be added to log
        assert caplog.text.endswith(log_text + "\n")

        logging.debug(entry_prefix + "2 debug")     # NOT logged
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "3 warning"
        logging.warning(log_text)                   # NOT logged
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "4 error logging"
        logging.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        # loggers
        log_text = entry_prefix + "4 error root"
        root_logger.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "4 error ae"
        ae_logger.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        log_text = entry_prefix + "4 error ae_cae"
        ae_cae_logger.error(log_text)
        assert caplog.text.endswith(log_text + "\n")

        # ConsoleAppEnv dpo
        sys.argv = ['tl_cdc']  # sys.argv has to be set for to allow get_option('debug_level') calls done by debug_out()
        new_log_text = entry_prefix + "5 dpo"
        cae.dpo(new_log_text, minimum_debug_level=DEBUG_LEVEL_DISABLED)
        assert caplog.text.endswith(log_text + "\n")
        cae.dpo(new_log_text, minimum_debug_level=DEBUG_LEVEL_DISABLED, logger=ae_cae_logger)
        assert caplog.text.endswith(new_log_text + "\n")

        # final checks of log file contents
        logging.shutdown()
        '''
        # .. logging.shutdown seems to do no flushing when run in combination with pytest within PyCharm
        if False and root_logger.handlers:
            root_logger.handlers[0].flush()
        else:
            [h_weak_ref().flush() for h_weak_ref in logging._handlerList]
            # or easier but less secure: [h.flush() for h in root_logger.handlerList]
        # .. even time.sleep(3..390) doesn't help
        # .. also tried:
        #         caplog.clear()
        #         caplog.handler.close()
        '''
        file_contents = delete_files(log_file, ret_type='contents')
        assert len(file_contents) >= 8
        for fc in file_contents:
            if fc.startswith("{TST}"):
                fc = fc[6:]  # remove sys_env_id prefix
            if fc.startswith("<"):
                fc = fc[fc.index("> ") + 2:]  # remove thread id prefix
            assert fc.startswith(entry_prefix) or fc.startswith('####  ') or fc.startswith('Ignorable ') or fc == ''
            #    or fc.startswith('_jb_pytest_runner ') or fc.startswith(tst_app_key) \
            #    or fc.lower().startswith('test  v 0.0') or fc.startswith('  **  Additional instance')
            assert "1 info" not in fc and "2 debug" not in fc and "3 warning" not in fc

    def test_app_instances_reset2(self):
        assert main_app_instance() is None


class TestConsoleAppBasics:
    def test_app_name(self, restore_app_env, sys_argv_app_key_restore):
        assert main_app_instance() is None
        name = 'tan_cae_name'
        sys.argv = [name, ]
        cae = ConsoleApp()
        assert cae.app_name == name
        assert main_app_instance() is cae

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_add_opt(self, restore_app_env):
        cae = ConsoleApp('test_add_opt')
        opt_name = 'test_opt'
        opt_val = 'test_opt_value'
        assert cae.get_option(opt_name) is None
        cae.add_opt(opt_name, 'test_opt_description', opt_val, short_opt='')
        assert cae.get_option(opt_name) == opt_val

    def test_set_opt(self, restore_app_env, sys_argv_app_key_restore):
        tst_val = 'test_init_value'
        cae = ConsoleApp('test_set_opt')
        cae.add_opt('test_opt', 'test_opt_description', tst_val)
        sys.argv = ['tso_pseudo_arg']
        assert cae.get_opt('test_opt') == tst_val
        tst_val = 'test_value'
        cae.set_opt('test_opt', tst_val, save_to_config=False)
        assert cae.get_opt('test_opt') == tst_val

        cae.set_opt('debug_level', DEBUG_LEVEL_VERBOSE, save_to_config=False)
        assert cae.get_opt('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_add_argument(self, restore_app_env):
        cae = ConsoleApp('test_add_argument')
        cae.add_argument('test_arg')

    def test_get_argument(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_get_argument')
        cae.add_argument('test_arg')
        arg_val = 'test_arg_val'
        sys.argv = ['test_app', arg_val]
        assert cae.get_argument('test_arg') == arg_val

    def test_debug_level_set_property(self, restore_app_env):
        cae = ConsoleApp()
        assert cae.debug_level == DEBUG_LEVEL_DISABLED
        cae.debug_level = DEBUG_LEVEL_VERBOSE
        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_show_help(self, restore_app_env):
        cae = ConsoleApp('test_show_help')
        cae.show_help()

    def test_sys_env_id(self, capsys, restore_app_env, sys_argv_app_key_restore):
        sei = 'tSt'
        cae = ConsoleApp('test_sys_env_id', sys_env_id=sei, debug_level=DEBUG_LEVEL_VERBOSE)
        assert cae.sys_env_id == sei
        cae.po(sei)     # increase coverage
        out, err = capsys.readouterr()
        assert sei in out

        # special case for error code path coverage
        ca2 = ConsoleApp('test_sys_env_id_COPY')
        assert ca2.sys_env_id == ''
        assert not ca2.get_opt('debug_level')

    def test_shutdown_basics(self, restore_app_env):
        def thr():
            """ thread """
            while running:
                pass

        cae = ConsoleApp('shutdown_basics')
        cae.shutdown(exit_code=None)

        activate_multi_threading()
        cae.shutdown(exit_code=None, timeout=0.6)       # tests freezing in debug run without timeout/thread-join

        running = True
        threading.Thread(target=thr).start()
        cae.shutdown(exit_code=None, timeout=0.6)
        running = False

    def test_shutdown_coverage(self, restore_app_env):
        cae = ConsoleApp('shutdown_coverage')
        cae.shutdown(exit_code=None, timeout=0.9)

        cae._log_file_index = 1
        cae.shutdown(exit_code=None, timeout=0.1)

        cae._nul_std_out = open(os.devnull, 'w')
        cae.shutdown(exit_code=None, timeout=0.1)

    def test_app_instances_reset2(self):
        assert main_app_instance() is None


class TestConfigOptions:
    def test_missing_cfg_file(self, restore_app_env):
        file_name = 'm_i_s_s_i_n_g' + INI_EXT
        cae = ConsoleApp('test_missing_cfg_file', additional_cfg_files=[file_name])
        assert not [f for f in cae._cfg_files if f.endswith(file_name)]

    def test_app_instances_reset1(self):
        assert main_app_instance() is None

    def test_get_var_basics(self, cons_app):
        cae = cons_app
        assert cae.get_var('debug_level') == DEBUG_LEVEL_DISABLED
        assert cae.get_var('un_declared_name') is None

    def test_get_var_env_options(self, cons_app):
        cae = cons_app
        vn = 'testVarName'
        assert cae.get_var(vn) is None

        vv = 'testVarValue'
        os.environ['AE_OPTIONS_TEST_VAR_NAME'] = vv
        assert cae.get_var(vn) == vv

    def test_get_var_env_section(self, cons_app):
        cae = cons_app
        vn = 'testVarName'
        assert cae.get_var(vn, section='aeSystems') is None

        vv = 'testVarValue'
        os.environ['AE_SYSTEMS_TEST_VAR_NAME'] = vv
        assert cae.get_var(vn, section='aeSystems') == vv

    def test_get_var_file_order(self, restore_app_env, config_fna_vna_vva):
        cwd_file, var_name, cwd_value = config_fna_vna_vva(file_name='test' + INI_EXT, var_value='cwd')
        cae = ConsoleApp('test_get_var_file_order', app_name='test')
        assert cae.get_var(var_name) == cwd_value                       # cwd variable

        usr_file, _, usr_value = config_fna_vna_vva(file_name='{usr}/test' + INI_EXT, var_value='usr')
        assert usr_file != cwd_file
        cae.add_cfg_files()
        cae.load_cfg_files()
        assert cae.get_var(var_name) == usr_value                       # usr variable overwrite cwd variable

        app_path = norm_path("{app}")
        if not os.path.exists(app_path):
            os.mkdir(app_path)  # will not be removed after test run!
        app_file, _, app_value = config_fna_vna_vva(file_name='{app}/test' + INI_EXT, var_value='app')
        assert app_file != cwd_file and app_file != usr_file
        cae.add_cfg_files()
        cae.load_cfg_files()
        assert cae.get_var(var_name) == app_value                       # usr_app variable overwrites cwd+usr variables

    def test_set_var_basics(self, restore_app_env, config_fna_vna_vva, sys_argv_app_key_restore):
        file_name, var_name, _ = config_fna_vna_vva(file_name='test' + INI_EXT)

        opt_test_val = 'opt_test_val'
        sys.argv = ['test', '-t=' + opt_test_val]

        cae = ConsoleApp('test_set_var_basics')
        cae.add_opt(var_name, 'test_config_basics', 'init_test_val', short_opt='')
        assert cae.get_opt(var_name) == opt_test_val

        val = 'test_value'
        assert not cae.set_var(var_name, val)
        assert cae.get_var(var_name) == val

        val = ('test_val1', 'test_val2')
        assert not cae.set_var(var_name, val)
        assert cae.get_var(var_name) == repr(val)

        val = datetime.datetime.now()
        assert not cae.set_var(var_name, val)
        assert cae.get_var(var_name) == val.strftime(DATE_TIME_ISO)

        val = datetime.date.today()
        assert not cae.set_var(var_name, val)
        assert cae.get_var(var_name) == val.strftime(DATE_ISO)

    def test_set_var_without_ini(self, restore_app_env, sys_argv_app_key_restore):
        var_name = 'test_config_var'
        cae = ConsoleApp('test_set_var_without_ini')
        cae.add_opt(var_name, 'test_set_var_without_ini', 'init_test_val', short_opt='t')
        opt_test_val = 'opt_test_val'
        sys.argv = ['test', '-t=' + opt_test_val]
        assert cae.get_opt(var_name) == opt_test_val

        val = 'test_value'
        assert cae.set_var(var_name, val)        # will be set, but returning error because test.ini does not exist
        assert cae.get_var(var_name) == val

        val = ('test_val1', 'test_val2')
        assert cae.set_var(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_var(var_name) == repr(val)

        val = datetime.datetime.now()
        assert cae.set_var(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_var(var_name) == val.strftime(DATE_TIME_ISO)

        val = datetime.date.today()
        assert cae.set_var(var_name, val)  # will be set, but returning error because test.ini does not exist
        assert cae.get_var(var_name) == val.strftime(DATE_ISO)

    def test_set_var_file_error(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_var_file_error', additional_cfg_files=[file_name])
        val = 'tt_value'
        # error in case of not existing ini file
        assert cae.set_var(var_name, val, cfg_fnam=os.path.join(os.getcwd(), 'not_existing' + INI_EXT))

        # error in case of invalid section name
        assert cae.set_var(var_name, val, section="]", cfg_fnam=file_name)

    def test_set_var_while_file_opened(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_var_while_file_opened', additional_cfg_files=[file_name])
        val = 'tst_value'

        with open(file_name, 'w'):      # although open file set_var() will not fail
            assert not cae.set_var(var_name, val, cfg_fnam=file_name)

    def test_set_var_with_reload(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_var_with_reload', additional_cfg_files=[file_name])
        val = 'test_value'
        assert not cae.set_var(var_name, val, cfg_fnam=file_name)

        cfg_val = cae.get_var(var_name)
        assert cfg_val == val

        cae.load_cfg_files()
        cfg_val = cae.get_var(var_name)
        assert cfg_val == val

    def test_set_var_no_option(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_var_no_option', additional_cfg_files=[file_name])
        val = 'any_test_value'
        section_name = 'tstSection'
        assert not cae.set_var(var_name, val, cfg_fnam=file_name, section=section_name)

        cfg_val = cae.get_var(var_name, section=section_name)
        assert cfg_val == val

    def test_set_var_with_rename(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva()
        cae = ConsoleApp('test_set_var_with_rename', additional_cfg_files=[file_name])
        val = 'test_value'
        new_var_name = 'new_tst_var_name'
        assert not cae.set_var(new_var_name, val, cfg_fnam=file_name, old_name=var_name)

        cfg_val = cae.get_var(var_name)
        assert cfg_val is None
        cfg_val = cae.get_var(new_var_name)
        assert cfg_val == val

    def test_multiple_option_single_char(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_multiple_option')
        sys.argv = ['test', "-Z=a", "-Z=1"]
        cae.add_opt('testMultipleOptionSC', 'test multiple option', [], 'Z', multiple=True)
        assert cae.get_opt('testMultipleOptionSC') == ['a', '1']

    def test_multiple_option_multi_char(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_multiple_option_multi_char')
        sys.argv = ['test', "-Z=abc", "-Z=123"]
        cae.add_opt('testMultipleOptionMC', 'test multiple option', [], short_opt='Z', multiple=True)
        assert cae.get_opt('testMultipleOptionMC') == ['abc', '123']

    def test_multiple_option_multi_values_fail(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_multiple_option_multi_val')
        sys.argv = ['test', "-Z", "abc", "123"]
        cae.add_opt('testMultipleOptionMV', 'test multiple option', [], short_opt='Z', multiple=True)
        with pytest.raises(SystemExit):
            cae.get_opt('testMultipleOptionMV')

    def test_multiple_option_single_char_with_choices(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_multiple_option_with_choices')
        sys.argv = ['test', "-Z=a", "-Z=1"]
        cae.add_opt('testAppOptChoicesSCWC', 'test multiple choices', [], 'Z', choices=['a', '1'], multiple=True)
        assert cae.get_opt('testAppOptChoicesSCWC') == ['a', '1']

    def test_multiple_option_stripped_value_with_choices(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_multiple_option_stripped_with_choices', cfg_opt_val_stripper=lambda v: v[-1])
        sys.argv = ['test', "-Z=x6", "-Z=yyy9"]
        cae.add_opt('testAppOptChoicesSVWC', 'test multiple choices', [], 'Z', choices=['6', '9'], multiple=True)
        assert cae.get_opt('testAppOptChoicesSVWC') == ['x6', 'yyy9']

    def test_multiple_option_single_char_fail_with_invalid_choices(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_multiple_option_fail_with_choices')
        sys.argv = ['test', "-Z=x", "-Z=9"]
        cae.add_opt('testAppOptChoices', 'test multiple choices', [], 'Z', choices=['a', '1'], multiple=True)
        with pytest.raises(ArgumentError):
            cae.get_opt('testAppOptChoices')     # == ['x', '9'] but choices is ['a', '1']

    def test_config_default_bool(self, restore_app_env):
        cae = ConsoleApp('test_config_defaults')
        cfg_val = cae.get_var('not_existing_config_var', default_value=False)
        assert cfg_val is False
        cfg_val = cae.get_var('not_existing_config_var2', value_type=bool)
        assert cfg_val is False

    def test_long_option_str_value(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_long_option_str_value')
        opt_val = 'testString'
        sys.argv = ['test', '--testStringOption=' + opt_val]
        cae.add_opt('testStringOption', 'test long option', '', 'Z')
        assert cae.get_opt('testStringOption') == opt_val

    def test_short_option_str_value(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_str_value')
        opt_val = 'testString'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testStringOption', 'test short option', '', 'Z')
        assert cae.get_opt('testStringOption') == opt_val

    def test_short_option_str_eval(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_str_eval')
        opt_val = 'testString'
        sys.argv = ['test', '-Z=""""' + opt_val + '""""']
        cae.add_opt('testString2Option', 'test str eval short option', '', 'Z')
        assert cae.get_opt('testString2Option') == opt_val

    def test_short_option_bool_str(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = 'False'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testBoolOption', 'test bool str option', True, 'Z')
        assert cae.get_opt('testBoolOption') is False

    def test_short_option_bool_number(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '0'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testBoolOption', 'test bool number option', True, 'Z')
        assert cae.get_opt('testBoolOption') is False

    def test_short_option_bool_number_true(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '1'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testBoolOption', 'test bool number option', False, 'Z')
        assert cae.get_opt('testBoolOption') is True

    def test_short_option_bool_eval(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '"""0 == 1"""'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testBoolOption', 'test bool eval option', True, 'Z')
        assert cae.get_opt('testBoolOption') is False

    def test_short_option_bool_eval_true(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_bool_str')
        opt_val = '"""9 == 9"""'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testBoolOption', 'test bool eval option', False, 'Z')
        assert cae.get_opt('testBoolOption') is True

    def test_short_option_date_str(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_date_str')
        opt_val = '2016-12-24'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testDateOption', 'test date str option', datetime.date.today(), 'Z')
        assert cae.get_opt('testDateOption') == datetime.date(year=2016, month=12, day=24)

    def test_short_option_datetime_str(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_datetime_str')
        opt_val = '2016-12-24 7:8:0.0'
        sys.argv = ['test', '-Z=' + opt_val]
        cae.add_opt('testDatetimeOption', 'test datetime str option', datetime.datetime.now(), 'Z')
        assert cae.get_opt('testDatetimeOption') == datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)

    def test_short_option_date_eval(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_date_eval')
        sys.argv = ['test', '-Z="""datetime.date(year=2016, month=12, day=24)"""']
        cae.add_opt('testDateOption', 'test date eval test option', datetime.date.today(), 'Z')
        assert cae.get_opt('testDateOption') == datetime.date(year=2016, month=12, day=24)

    def test_short_option_datetime_eval(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_datetime_eval')
        sys.argv = ['test', '-Z="""datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)"""']
        cae.add_opt('testDatetimeOption', 'test datetime eval test option', datetime.datetime.now(), 'Z')
        assert cae.get_opt('testDatetimeOption') == datetime.datetime(year=2016, month=12, day=24, hour=7, minute=8)

    def test_short_option_list_str(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_list_str')
        opt_val = [1, 2, 3]
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_opt('testListStrOption', 'test list str option', [], 'Z')
        assert cae.get_opt('testListStrOption') == opt_val

    def test_short_option_list_eval(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_list_eval')
        sys.argv = ['test', '-Z="""[1, 2, 3]"""']
        cae.add_opt('testListEvalOption', 'test list eval option', [], 'Z')
        assert cae.get_opt('testListEvalOption') == [1, 2, 3]

    def test_short_option_dict_str(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_dict_str')
        opt_val = {'a': 1, 'b': 2, 'c': 3}
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_opt('testDictStrOption', 'test list str option', {}, 'Z')
        assert cae.get_opt('testDictStrOption') == opt_val

    def test_short_option_dict_eval(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_dict_eval')
        sys.argv = ['test', "-Z='''{'a': 1, 'b': 2, 'c': 3}'''"]
        cae.add_opt('testDictEvalOption', 'test dict eval option', {}, 'Z')
        assert cae.get_opt('testDictEvalOption') == {'a': 1, 'b': 2, 'c': 3}

    def test_short_option_tuple_str(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_tuple_str')
        opt_val = ('a', 'b', 'c')
        sys.argv = ['test', '-Z=' + repr(opt_val)]
        cae.add_opt('testTupleStrOption', 'test tuple str option', (), 'Z')
        assert cae.get_opt('testTupleStrOption') == opt_val

    def test_short_option_tuple_eval(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_tuple_eval')
        sys.argv = ['test', "-Z='''('a', 'b', 'c')'''"]
        cae.add_opt('testDictEvalOption', 'test tuple eval option', (), 'Z')
        assert cae.get_opt('testDictEvalOption') == ('a', 'b', 'c')

    def test_config_str_eval_single_quote(self, config_fna_vna_vva):
        opt_val = 'testString'
        file_name, var_name, _ = config_fna_vna_vva(var_value="''''" + opt_val + "''''")
        cae = ConsoleApp('test_config_str_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == opt_val

    def test_config_str_eval_double_quote(self, config_fna_vna_vva, restore_app_env):
        opt_val = 'testString'
        file_name, var_name, _ = config_fna_vna_vva(var_value='""""' + opt_val + '""""')
        cae = ConsoleApp('test_config_str_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == opt_val

    def test_config_bool_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='True')
        cae = ConsoleApp('test_config_bool_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name, value_type=bool) is True

    def test_config_bool_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""1 == 0"""')
        cae = ConsoleApp('test_config_bool_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) is False

    def test_config_bool_eval_true(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""6 == 6"""')
        cae = ConsoleApp('test_config_bool_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) is True

    def test_config_date_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='2012-12-24')
        cae = ConsoleApp('test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name, value_type=datetime.date) == datetime.date(year=2012, month=12, day=24)

    def test_config_date_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""datetime.date(year=2012, month=12, day=24)"""')
        cae = ConsoleApp('test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == datetime.date(year=2012, month=12, day=24)

    def test_config_datetime_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='2012-12-24 7:8:0.0')
        cae = ConsoleApp('test_config_date_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name, value_type=datetime.datetime) \
            == datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)

    def test_config_datetime_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(
            var_value='"""datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)"""')
        cae = ConsoleApp('test_config_datetime_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == datetime.datetime(year=2012, month=12, day=24, hour=7, minute=8)

    def test_config_list_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='[1, 2, 3]')
        cae = ConsoleApp('test_config_list_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == [1, 2, 3]

    def test_config_list_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""[1, 2, 3]"""')
        cae = ConsoleApp('test_config_list_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == [1, 2, 3]

    def test_config_dict_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value="{'a': 1, 'b': 2, 'c': 3}")
        cae = ConsoleApp('test_config_dict_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == {'a': 1, 'b': 2, 'c': 3}

    def test_config_dict_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""{"a": 1, "b": 2, "c": 3}"""')
        cae = ConsoleApp('test_config_dict_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == {'a': 1, 'b': 2, 'c': 3}

    def test_config_tuple_str(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value="('a', 'b', 'c')")
        cae = ConsoleApp('test_config_tuple_str', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == ('a', 'b', 'c')

    def test_config_tuple_eval(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, _ = config_fna_vna_vva(var_value='"""("a", "b", "c")"""')
        cae = ConsoleApp('test_config_tuple_eval', additional_cfg_files=[file_name])
        assert cae.get_var(var_name) == ('a', 'b', 'c')

    def test_base_debug_level_add_opt_default(self, restore_app_env):
        cae = ConsoleApp('test_add_opt_default', debug_level=DEBUG_LEVEL_VERBOSE)
        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_short_option_value(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_value')
        sys.argv = ['test', '-D=' + str(DEBUG_LEVEL_VERBOSE)]
        cae.run_app()
        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_long_option_value(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_long_option_value')
        sys.argv = ['test', '--debug_level=' + str(DEBUG_LEVEL_VERBOSE)]
        cae.run_app()
        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_short_option_eval_single_quoted(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_quoted_option_eval')
        sys.argv = ["test", "-D='''int('" + str(DEBUG_LEVEL_VERBOSE) + "')'''"]
        cae.run_app()
        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_short_option_eval_double_quoted(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_double_quoted_option_eval')
        sys.argv = ['test', '-D="""int("' + str(DEBUG_LEVEL_VERBOSE) + '")"""']
        cae.run_app()
        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_config_default(self, restore_app_env, config_fna_vna_vva, sys_argv_app_key_restore):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debug_level', var_value=str(DEBUG_LEVEL_VERBOSE))
        cae = ConsoleApp('test_config_default', additional_cfg_files=[file_name])
        sys.argv = [sys_argv_app_key_restore, ]
        cae.run_app()
        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_base_debug_level_config_eval_single_quote(self, restore_app_env, config_fna_vna_vva,
                                                       sys_argv_app_key_restore):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debug_level',
                                                    var_value="'''int('" + str(DEBUG_LEVEL_VERBOSE) + "')'''")
        cae = ConsoleApp('test_config_eval', additional_cfg_files=[file_name])
        sys.argv = [sys_argv_app_key_restore, ]
        cae.run_app()
        assert cae.debug_level == DEBUG_LEVEL_VERBOSE

    def test_debug_level_short_option_value(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_option_value')
        sys.argv = ['test', '-D=' + str(DEBUG_LEVEL_VERBOSE)]
        assert cae.get_opt('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_debug_level_long_option_value(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_long_option_value')
        sys.argv = ['test', '--debug_level=' + str(DEBUG_LEVEL_VERBOSE)]
        assert cae.get_opt('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_debug_level_short_option_eval_single_quoted(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_quoted_option_eval')
        sys.argv = ["test", "-D='''int('" + str(DEBUG_LEVEL_VERBOSE) + "')'''"]
        assert cae.get_opt('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_debug_level_short_option_eval_double_quoted(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_double_quoted_option_eval')
        sys.argv = ['test', '-D="""int("' + str(DEBUG_LEVEL_VERBOSE) + '")"""']
        assert cae.get_opt('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_debug_level_config_default(self, restore_app_env, config_fna_vna_vva, sys_argv_app_key_restore):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debug_level', var_value=str(DEBUG_LEVEL_VERBOSE))
        cae = ConsoleApp('test_config_default', additional_cfg_files=[file_name])
        sys.argv = [sys_argv_app_key_restore, ]
        assert cae.get_opt(var_name) == DEBUG_LEVEL_VERBOSE

    def test_debug_level_config_eval_single_quote(self, restore_app_env, config_fna_vna_vva, sys_argv_app_key_restore):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debug_level',
                                                    var_value="'''int('" + str(DEBUG_LEVEL_VERBOSE) + "')'''")
        cae = ConsoleApp('test_config_eval', additional_cfg_files=[file_name])
        sys.argv = [sys_argv_app_key_restore, ]
        assert cae.get_opt(var_name) == DEBUG_LEVEL_VERBOSE

    def test_debug_level_config_eval_double_quote(self, restore_app_env, config_fna_vna_vva, sys_argv_app_key_restore):
        file_name, var_name, _ = config_fna_vna_vva(var_name='debug_level',
                                                    var_value='"""int("' + str(DEBUG_LEVEL_VERBOSE) + '")"""')
        cae = ConsoleApp('test_config_double_eval', additional_cfg_files=[file_name])
        sys.argv = [sys_argv_app_key_restore, ]
        assert cae.get_opt(var_name) == DEBUG_LEVEL_VERBOSE

    def test_sys_env_id_with_debug(self, restore_app_env, sys_argv_app_key_restore):
        cae = ConsoleApp('test_sys_env_id_with_debug', sys_env_id='OTHER')
        sys.argv = ['test', '-D=' + str(DEBUG_LEVEL_VERBOSE)]
        assert cae.get_opt('debug_level') == DEBUG_LEVEL_VERBOSE

    def test_config_main_file_not_modified(self, config_fna_vna_vva, restore_app_env):
        config_fna_vna_vva(
            file_name=os.path.join(os.getcwd(), os.path.splitext(os.path.basename(sys.argv[0]))[0] + INI_EXT))
        cae = ConsoleApp('test_config_modified_after_startup')
        assert not cae.is_main_cfg_file_modified()

    def test_is_main_cfg_file_modified(self, config_fna_vna_vva, restore_app_env):
        file_name, var_name, old_var_val = config_fna_vna_vva(
            file_name=os.path.join(os.getcwd(), os.path.splitext(os.path.basename(sys.argv[0]))[0] + INI_EXT))
        cae = ConsoleApp('test_set_var_with_reload')
        time.sleep(.963)    # needed because Python is too quick, especially on github-ci (fails sometimes with 0.639)
        new_var_val = 'NEW_test_value'
        assert not cae.set_var(var_name, new_var_val)
        assert cae.is_main_cfg_file_modified()

        # cfg_val has already new value (NEW_test_value) because parser instance got reloaded
        cfg_val = cae.get_var(var_name)
        assert cfg_val != old_var_val
        assert cfg_val == new_var_val
        assert cae.is_main_cfg_file_modified()

        cae.load_cfg_files()
        cfg_val = cae.get_var(var_name)
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
