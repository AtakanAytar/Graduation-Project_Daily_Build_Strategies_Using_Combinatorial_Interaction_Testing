import sys
import json
import random
import os
import copy
import datetime 
import shutil
import logging
import pprint
import pathlib
import re
import subprocess
from contextlib import redirect_stdout
import time
import ntpath
import xml.etree.ElementTree as et
import itertools
from bs4 import BeautifulSoup
from itertools import combinations , product


# get a pretty printer
pp = pprint.PrettyPrinter(indent=2)

# get a logger
log_formatter = logging.Formatter('%(asctime)-15s: %(message)s')
logger = logging.getLogger('main')
logger.setLevel(logging.INFO)
log_console_handler = logging.StreamHandler()
log_console_handler.setLevel(logging.INFO)
log_console_handler.setFormatter(log_formatter)
logger.addHandler(log_console_handler)

default_stdout = sys.stdout
default_stderr = sys.stderr

curr_stdout = default_stdout
curr_stderr = default_stderr


class ConfigSpaceModel:

    def __init__(self, model_file):
        self.model_file = model_file
        self.model = None
        self.no_of_opts = 0
        self.opt2idx = {}
        self.idx2opt = {}
        self.setting2idx = {}
        self.idx2setting = {}
        self.options = {}
        self.parse()
        
    def parse(self):

        # parse the json file
        with open(self.model_file) as json_file:
            self.model = json.load(json_file)

        # create the opt2idx and idx2opt dictionaries
        opt_idx = 0
        for opt in self.model['options']:
            self.options[opt['option']] = opt
            self.opt2idx[opt['option']] = opt_idx
            self.idx2opt[opt_idx] = opt['option']

            self.setting2idx[opt['option']] = {}
            self.idx2setting[opt_idx] = {}            
            setting_idx = 0
            for setting in opt['settings']:
                self.setting2idx[opt['option']][setting] = setting_idx
                self.idx2setting[opt_idx][setting_idx] = setting            
                setting_idx += 1
                
            opt_idx += 1

        self.no_of_opts = opt_idx
        
        return self.model
 
    def get_compile_time_cfg(self, cfg):

        compile_time_cfg = []
        
        for opt_idx in range(len(cfg)):
            opt = self.options[self.idx2opt[opt_idx]]
            if opt['type'] == 'compile-time':
                compile_time_cfg.append(cfg[opt_idx])

        return compile_time_cfg

    def get_run_time_cfg(self, cfg):

        run_time_cfg = []
        
        for opt_idx in range(len(cfg)):
            opt = self.options[self.idx2opt[opt_idx]]
            if opt['type'] == 'run-time':
                run_time_cfg.append(cfg[opt_idx])

        return run_time_cfg

    def cfg2str(self, cfg):
        if len(cfg) != self.no_of_opts:
            sys.exit("FATAL: not every option has a setting in cfg\n  " + str(cfg) + "\n  no of options should be: " + str(self.no_of_opts))

        cfg_str = []
        for opt_idx in range(len(cfg)):
            opt_name = self.idx2opt[opt_idx]
            cfg_str.append(opt_name + '=' + cfg[opt_idx])
        cfg_str = '[' + ', '.join(cfg_str) + ']'

        return cfg_str

    def cfg2idx(self, cfg):
        if len(cfg) != self.no_of_opts:
            sys.exit("FATAL: not every option has a setting in cfg\n  " + str(cfg) + "\n  no of options should be: " + str(self.no_of_opts))

        cfg_idx = []
        for opt_idx in range(len(cfg)):
            setting_idx = self.setting2idx[self.idx2opt[opt_idx]][cfg[opt_idx]]
            cfg_idx.append(setting_idx)

        return cfg_idx


    def idx2cfg(self, cfg_idx):
        if len(cfg_idx) != self.no_of_opts:
            sys.exit("FATAL: not every option has a setting in cfg\n  " + str(cfg_idx) + "\n  no of options should be: " + str(self.no_of_opts))

        cfg = []
        for opt_idx in range(len(cfg_idx)): 
            setting = self.idx2setting[opt_idx][cfg_idx[opt_idx]]
            cfg.append(setting)

        return cfg
    
    def get_model(self):
        return self.model


    
def date_to_dir_name(date):
    # year_month_day_hour_minute_seconds
    return date.strftime('%Y_%m_%d_%H_%M_%S')

def cfg_to_dir_name(cfg):

    dir_name = ''
    
    for elm in cfg:
        dir_name += str(elm) + '_'

    # remove the last '_'
    dir_name = re.sub('\_$', '', dir_name)
    
    return dir_name


def remove_dir(my_dir):
    # For security reasons we are only removing directories
    # the name of which is work

    target_dir = re.compile("([^\\\/]+)$").search(my_dir).group(1)
    if target_dir != 'work':
        logger.fatal("FATAL: A directory the name of which ('%s') is not 'work' attempted to be removed. Exiting..." % my_dir)
        sys.exit(-1)

    shutil.rmtree(my_dir, ignore_errors=True, onerror=None)
        
    
def reset_output_streams():

    sys.stdout = default_stdout
    sys.stderr = default_stderr
    
    curr_stdout = default_stdout
    curr_stderr = default_stderr

def run_cmd(cmd):
    global curr_stdout
    global curr_stderr

    proc = subprocess.Popen(cmd,
                            stdout=curr_stdout,
                            stderr=curr_stderr,
                            universal_newlines=True)
    proc.communicate()
    
def remove_file(file_name):
    if os.path.isfile(file_name):
        os.remove(file_name)

def print_to_file(content, file_name):
    with open(file_name, 'w') as f:
        f.write(content)
        
class SUT_ADAPTER:
    def __init__(self, sut):
        self.sut = sut
 
    def get_name(self):
        return self.sut.get_name()

    def get_version(self):
        return self.sut.get_version()

    def get_curr_config(self):
        return self.sut.curr_config

    def set_curr_config(self, cfg):
        self.sut.curr_config = cfg

    def get_static_config_found(self):
        return self.sut.static_config_found

    def set_static_config_found(self, static_config_found):
        self.sut.static_config_found = static_config_found
        
    def get_config_space_model(self):
        return self.sut.config_space_model
    
    def get_workdir(self):
        return self.sut.get_workdir()

    def set_workdir(self, workdir):
        return self.sut.set_workdir(workdir)

    def get_compile_time_cfg(self, cfg):
        return self.sut.config_space_model.get_compile_time_cfg(cfg)

    def get_run_time_cfg(self, cfg):
        return self.sut.config_space_model.get_run_time_cfg(cfg)

    def cfg2idx(self, cfg):
        return self.sut.config_space_model.cfg2idx(cfg)
        
    def idx2cfg(self, cfg_idx):
        return self.sut.config_space_model.idx2cfg(cfg_idx)

    def redirect_output(self, out_file):
        global curr_stdout
        global curr_stderr
        
        reset_output_streams()

        curr_stdout = open(out_file, 'a+')
        curr_stderr = curr_stdout

        sys.stdout = curr_stdout
        sys.stderr = curr_stderr

    def reset_output_redirection(self):
        if curr_stdout is not None and curr_stdout != default_stdout:
            curr_stdout.close()

        reset_output_streams()
        
    def download(self, date_time, download_dir):
        global curr_stdout
        global curr_stderr

        if os.path.isdir(download_dir):
            logger.fatal("FATAL: download directory '%s' exists for sut %s. Exiting..." % (download_dir, self.sut.get_name()))
            sys.exit(-1)

        log_file = os.getcwd() + os.sep + 'download.log'
        remove_file(log_file)

        self.redirect_output(log_file)

        self.sut.download(date_time, download_dir)
                
        self.reset_output_redirection()
         
        # move the log file to the download directory
        download_log_file = download_dir + os.sep + 'download.log'
        shutil.move(log_file, download_log_file)

        log = self.sut.harvest_download_log(download_log_file)

        # Note that we assume that the log dictiory has field called success
        #  which will indicate whether the operation was successfull or not
        success = log['success']        
        parsed_log_file = download_log_file + '.parsed'
        remove_file(parsed_log_file)
        print_to_file(json.dumps(log, indent=2), parsed_log_file)
        
        return log

    def configure(self, cfg, static_config_found):

        log_file = self.sut.get_workdir() + os.sep + 'configure.log'
        remove_file(log_file)

        self.redirect_output(log_file)

        configured = self.sut.configure(cfg, static_config_found)
        
        self.reset_output_redirection()

        # Parse the log file
        log = self.sut.harvest_configure_log(log_file)
        
        success = log['success']        
        #parsed_log_file = log_file + '.parsed'
        #remove_file(parsed_log_file)
        #print_to_file(json.dumps(log, indent=2), parsed_log_file)
        
        return log
    
    
    def build(self):

        log_file = self.sut.get_workdir() + os.sep + 'build.log'
        remove_file(log_file)

        self.redirect_output(log_file)

        self.sut.build()
        
        self.reset_output_redirection()

        # Parse the log file
        log = self.sut.harvest_build_log(log_file)
        
        success = log['success']        
        #parsed_log_file = log_file + '.parsed'
        #remove_file(parsed_log_file)
        #print_to_file(json.dumps(log, indent=2), parsed_log_file)
        
        return log
    
        
    def run_tests(self):
        
        log_file = self.sut.get_workdir() + os.sep + 'tests.log'
        remove_file(log_file)

        self.redirect_output(log_file)

        self.sut.run_tests()
        
        self.reset_output_redirection()

        # Parse the log file
        log = self.sut.harvest_tests_log(log_file)
        
        success = log['success']        
        #parsed_log_file = log_file + '.parsed'
        #remove_file(parsed_log_file)
        #print_to_file(json.dumps(log, indent=2), parsed_log_file)
            
        return log

    def daily_harvest(self, in_dir):

        #here
        log_file = in_dir + os.sep + 'daily_harvest.log'
        remove_file(log_file)

        self.redirect_output(log_file)
        
        harvest = self.sut.daily_harvest(in_dir)
        
        self.reset_output_redirection()
        
        return harvest

def daily_build(app_under_test, date, ca, archive_dir, archive_id, work_dir=None):

    # set the work_dir if needed
    if work_dir is None:
        work_dir = archive_dir + os.sep + 'work'

    # Create the archive_root_dir
    os_sep = os.sep
    archive_root_dir = archive_dir + os.sep + os_sep.join(archive_id)
    day_archive_dir = archive_root_dir + os.sep + 'daily_builds' + os.sep + date_to_dir_name(date)
    pathlib.Path(day_archive_dir).mkdir(parents=True, exist_ok=True)

    # save the ca under the day_arhive_dir just incase something bad happens
    with open(day_archive_dir + os.sep + 'ca.txt', "w") as caf:
        for cfg in ca:
            caf.write(','.join(cfg) + '\n')
        
    # create the sut adapter so that we can work with
    # the sut
    sut = SUT_ADAPTER(app_under_test)

    # size of the covering array to be executed
    ca_size = len(ca)
    
    logger.info("###########################")
    logger.info("SUT         : %s" % sut.get_name())
    logger.info("VERSION     : %s" % sut.get_version())
    logger.info("DATE        : %s" % str(date))
    logger.info("CA SIZE     : %d" % ca_size)
    logger.info("WORKDIR     : %s" % work_dir)
    logger.info("ARCHIVE_DIR : %s" % archive_root_dir)
    logger.info("")
    
    # Create the archive_dir
    pathlib.Path(archive_dir).mkdir(parents=True, exist_ok=True)
    
    # Create the vanilla builds directory
    # This is directory we store the vanillan versions of the
    # static builds
    vanilla_builds_dir = archive_dir + os.sep + 'static_builds'
    pathlib.Path(vanilla_builds_dir).mkdir(parents=True, exist_ok=True)
    # This is the date-based vanilla dir. Note that version of the system
    # may change depending on the date
    vanilla_dir = vanilla_builds_dir + os.sep + date_to_dir_name(date)
    pathlib.Path(vanilla_dir).mkdir(parents=True, exist_ok=True)

    # source repository where the source code is stored
    source_repository = archive_dir + os.sep + 'source_repository'
    source_repository_dir = source_repository + os.sep + date_to_dir_name(date)
    
    # DOWNLOAD
    download_log = None
    if os.path.isdir(source_repository_dir):
        logger.info("No need for downloading the source as it already exists")
        download_log_file = source_repository_dir + os.sep + 'download.log.parsed'
        if os.path.isfile(download_log_file):
            with open(download_log_file) as json_file:
                download_log = json.load(json_file)            
            downloaded = download_log['success']
        else:
            downloaded = False

    else:
        logger.info("Downloading %s %s on %s" % (sut.get_name(), sut.get_version(), date))
        download_log = sut.download(date, source_repository_dir)
        downloaded = download_log['success']
        
    if not downloaded:
        logger.fatal("   FATAL: Not downloaded!")
        return False

    # test each configuration in the given covering array
    for i in range(len(ca)):
        cfg = ca[i]
        cfg_idx = i + 1

        logger.info("")
        logger.info("CFG %d out of %d:" % (cfg_idx, ca_size))

        # Remove the work direactory if exists
        remove_dir(work_dir)

        # set the work directory for the sut
        sut.set_workdir(work_dir)
        
        # get the compile time configuration
        # If we have already build this configuration use it
        # instead of recreating it

        static_config = None
        static_config_dir = None
        has_static_config = False
        static_config_found = False
        if len(sut.get_compile_time_cfg(sut.cfg2idx(cfg))) > 0:
            has_static_config = True
            static_config = cfg_to_dir_name(sut.get_compile_time_cfg(sut.cfg2idx(cfg))) 
            static_config_dir = vanilla_dir + os.sep + static_config
            
            # check to see we have already compiled this static config
            static_config_found = False
            if os.path.isdir(static_config_dir):
                # Copy the pre-build system over
                shutil.copytree(static_config_dir, work_dir)
                static_config_found = True

        if (not has_static_config) or (not static_config_found):
            # We need to build the system from scratch
            # copy the source directory
            shutil.copytree(source_repository_dir, work_dir)
            
        # CONFIGURE
        logger.info("   Configuring...")

        if static_config_found:
            logger.info("     Pre-built static configuration has been found." )

        configure_log = sut.configure(cfg, static_config_found)
        configured = configure_log['success']
                
        if not configured:
            logger.error("     ERROR: SUT not configured with configuration #%d!" % cfg_idx)
            continue # skip this configuration
            
        # BUILD
        logger.info("   Building...")
        if static_config_found:
            logger.info("     Pre-built static configuration has been found." )

        build_log = sut.build()
        built = build_log['success']
                
        if not built:
            logger.error("     ERROR: SUT did not build ")
            continue # skip this configuration

        # Before running the test cases, if we need to get a copy of the static
        # configuration do it.
        
        if (has_static_config) and (not static_config_found):
            logger.info("     Copying the build to static configs repository...")
            # copy the work directory
            shutil.copytree(work_dir, static_config_dir)
 
        # RUN TESTS
        logger.info("   Testing...")

        tests_log = sut.run_tests()
        tested = tests_log['success']

        if not tested:
            logger.error("     ERROR: Could not run the testcases.")
            continue # skip this configuration

        # HARVEST
        logger.info("   Harvesting...")

        harvest = {'date':str(date),
                   'cfg_idx':cfg_idx,
                   'cfg':cfg,
                   'download_log':download_log,
                   'configure_log':configure_log,
                   'build_log':build_log,
                   'tests_log':tests_log }
        harvest_file = work_dir +  os.sep + 'harvest.json'        
        print_to_file(json.dumps(harvest, indent=2), harvest_file)                

        # Now it is time to archive the work
        my_archive_dir = day_archive_dir + os.sep + 'cfg_' + str(cfg_idx)
        shutil.copytree(work_dir, my_archive_dir)

        logger.info("   Archiving under '%s'." % my_archive_dir)
    
    logger.info("Performing daily harvest...")
    
    harvest = sut.daily_harvest(day_archive_dir)                    
    harvest_daily_file = day_archive_dir +  os.sep + 'harvest_daily.json'        
    print_to_file(json.dumps(harvest, indent=2), harvest_daily_file)                

    # Remove the work directory as we are done
    remove_dir(work_dir)
    
    logger.info("###########################")

    return True
    
# base class for the suts

class SUT:

    def __init__(self, name, version, config_space_model_file):
        self.name = name
        self.version = version
        self.config_space_model_file = config_space_model_file
        self.workdir = None
        self.curr_config = None
        self.static_config_found = None
        if config_space_model_file is None:
            self.config_space_model = None
        else:
            self.config_space_model = ConfigSpaceModel(self.config_space_model_file)

    def get_name(self):
        return self.name

    def get_version(self):
        return self.version

    def get_curr_config(self):
        return self.curr_config

    def set_curr_config(self, cfg):
        self.curr_config = cfg

    def get_static_config_found(self):
        return self.static_config_found

    def set_static_config_found(self, static_config_found):
        self.static_config_found = static_config_found

    def get_config_space_model(self):
        return self.config_space_model
    
    def get_workdir(self):
        return self.workdir

    def set_workdir(self, workdir):
        self.workdir = workdir
    
    def get_compile_time_cfg(self, cfg):
        return self.config_space_model.get_compile_time_cfg(cfg)

    def get_run_time_cfg(self, cfg):
        return self.config_space_model.get_run_time_cfg(cfg)

    def cfg2idx(self, cfg):
        return self.config_space_model.cfg2idx(cfg)
        
    def idx2cfg(self, cfg_idx):
        return self.config_space_model.idx2cfg(cfg_idx)
            
    def download(self, date_time, download_dir):
        return False

    def configure(self, cfg, static_config_found):
        return False
        
    def build(self):
        return False

    def run_tests(self):
        return False

    def daily_harvest(self, in_dir):
        return False

    def harvest_all(self, in_dir):
        return False

    def harvest_build_log(self, log_file):
        return {'success':False}

    def harvest_configure_log(self, log_file):
        return {'success':False}

    def harvest_tests_log(self, log_file):
        return {'success':False}

    def harvest_download_log(self, log_file):
        return {'success':False}

class DailyBuildStrategy:
    
    def __init__(self, args):
        self.args = args
        self.name = None

    def get_name(self):
        return self.name

    def name_to_dir_name(self):
        return self.name
    
    def args_to_dir_name(self):
        return None

    def generate_plan(self, sut, plan, strategy_plan_dir):
        return None    
    
    def mark_covered_tuples(self, covering_array, config_model, t, 
                            uncovered_tuples):
        opt_count = len(config_model.options)
        for cfg in covering_array:
            for opt_comb_idx in itertools.combinations(range(opt_count), t):
                opt_comb = tuple([config_model.idx2opt[optidx] 
                                  for optidx in opt_comb_idx])
                cfg_tuple = tuple([cfg[optidx] for optidx in opt_comb_idx])
                if cfg_tuple in uncovered_tuples[opt_comb]:
                    uncovered_tuples[opt_comb].remove(cfg_tuple)      
  
    def coverage_measurement_ca(self, covering_array, config_model, t, uncovered_tuples):
        opt_count = len(config_model.options)
        covered_tuples = 0
        for opt_comb_idx in itertools.combinations(range(opt_count), t):
            opt_comb = tuple([config_model.idx2opt[optidx] for optidx in opt_comb_idx])
            for set_comb in uncovered_tuples[opt_comb]:
                covered = False
                for cfg in covering_array:
                    cfg_tuple = tuple([cfg[optidx] for optidx in opt_comb_idx])
                    if cfg_tuple == set_comb:
                        covered = True
                        break
                if covered:
                    covered_tuples += 1
        return covered_tuples
             
    def count_uncovered_tuples(self, covered_tuples):
        count = 0
        for opt_comb in covered_tuples:
            count += len(covered_tuples[opt_comb])
        return count
            
    def priotrize_plan(self, covering_arrays, config_model, t,
                       strategy_plan_dir):
        priorized_cas = []
        options = config_model.options
        uncovered_tuples = {}
        
        # Generate all t-tuples
        for opt_comb in itertools.combinations(options.keys(), t):
            uncovered_tuples[opt_comb] = set()
            settings = [options[option]["settings"] for option in opt_comb]
            for sett_comb in itertools.product(*settings):
                uncovered_tuples[opt_comb].add(sett_comb)
        
        # priotrize covering arrays
        caidxes = [x for x in range(len(covering_arrays))]
        while len(caidxes) > 0:
            uncovered_tuple_count = self.count_uncovered_tuples(uncovered_tuples)
            max_coverage = -1000
            max_covered_caidx = -1000
            for caidx in caidxes:
                ca = covering_arrays[caidx]
                covered_tuples = self.coverage_measurement_ca(ca, config_model, t, 
                                                             uncovered_tuples)
                if max_coverage < covered_tuples:
                    max_coverage = covered_tuples
                    max_covered_caidx = caidx
            chosen_ca = covering_arrays[max_covered_caidx]
            priorized_cas.append(chosen_ca)
            self.mark_covered_tuples(chosen_ca, config_model, t, uncovered_tuples)
            caidxes.remove(max_covered_caidx)
            # TODO: update uncovered tuples
        
        uncovered_tuples.clear()
        for opt_comb in itertools.combinations(options.keys(), t):
            uncovered_tuples[opt_comb] = set()
            settings = [options[option]["settings"] for option in opt_comb]
            for sett_comb in itertools.product(*settings):
                uncovered_tuples[opt_comb].add(sett_comb)
        
        # priotrize configurations
        uncovered_tuple_count = 0
        priorized_cas_and_cfgs = []
        out_file_coverage_info = open(strategy_plan_dir + os.sep + "coverage_info.csv", 'w')
        out_file_coverage_info.write("ca_idx,cfg_idx,covered_tuples\n")
        
        caidxes = [x for x in range(len(covering_arrays))]
        for caidx in caidxes:
            ca = priorized_cas[caidx]
            priorized_cfgs = []  # new CA
            cfgidxes = [x for x in range(len(ca))]
            while len(cfgidxes) > 0:
                uncovered_tuple_count = self.count_uncovered_tuples(uncovered_tuples)
                max_coverage = -1000
                max_covered_cfgidx = -1000
                for cfgidx in cfgidxes:
                    cfg = ca[cfgidx]
                    covered_tuples = self.coverage_measurement_ca([cfg], config_model, t, 
                                                           uncovered_tuples)
                    if max_coverage < covered_tuples:
                        max_coverage = covered_tuples
                        max_covered_cfgidx = cfgidx
                chosen_cfg = ca[max_covered_cfgidx]
                priorized_cfgs.append(list(chosen_cfg))
                out_file_coverage_info.write(",".join([str(caidx), str(cfgidx), str(max_coverage)]) + "\n")
                self.mark_covered_tuples([chosen_cfg], config_model, t, uncovered_tuples)
                cfgidxes.remove(max_covered_cfgidx)
            priorized_cas_and_cfgs.append(priorized_cfgs)
        out_file_coverage_info.close()
        return priorized_cas_and_cfgs  
            


# For deep equality check

def ordered(obj):
    if isinstance(obj, dict):
        return sorted((k, ordered(v)) for k, v in obj.items())
    if isinstance(obj, list):
        return [ordered(x) for x in obj]
    else:
        return obj

def run_experiment(sut, config_space_model_file,
                   start_date, end_date,
                   strategies,
                   archive_dir):

    # create the sut object
    sut = eval(sut + "('" + config_space_model_file + "')")
    sut_name = sut.get_name()
    sut_archive_dir = archive_dir + os.sep + sut_name
    pathlib.Path(sut_archive_dir).mkdir(parents=True, exist_ok=True)

    # handle the config space model file

    # if the config space model file is None
    # the use the model file under the sut_archive_dir
    model_file = sut_archive_dir + os.sep + 'config_model.txt'
    if config_space_model_file is None:
        if not os.path.isfile(model_file):
            logger.fatal("FATAL: Noe config space model is given and file '%s' does not exist. Exiting..." % model_file)
            sys.exit(-1)

    else: 
        if os.path.isfile(model_file):
            # Check to see if they are the same configuration file if not fail
            # because everything under the sut_archive_dir will be with respect
            # to the configuration space model file

            # read the provided model file
            given_model = None
            with open(config_space_model_file) as json_file:
                given_model = json.load(json_file)

            # read the existing model file
            existing_model = None
            with open(model_file) as json_file:
                existing_model = json.load(json_file)

            if not ordered(given_model) == ordered(existing_model):
                logger.fatal("Given configuration model and the existing one do not match. Exiting...")
                logger.fatal("   Given    : '%s'" % config_space_model_file)
                logger.fatal("   Existing : '%s'" % model_file)
                sys.exit(-1)
        else:
            # copy the configuration file
            shutil.copy(config_space_model_file, model_file)

    # Ok, configuration file is in place
    # So, we are ready to go

    for strategy in strategies:
        strategy_name = strategy['name']
        strategy_args = strategy['args']

        # create the strateg*y
        strategyObj = eval(strategy_name + "(" + str(strategy_args)+ ")")

        strategy_args_id = strategyObj.args_to_dir_name()
        strategy_archive_id = [strategy_name, strategy_args_id]
        strategy_dir = sut_archive_dir + os.sep + strategy_name + os.sep + strategy_args_id
        strategy_plan_dir = strategy_dir + os.sep + 'plan'
        pathlib.Path(strategy_plan_dir).mkdir(parents=True, exist_ok=True)
    
        # Now, you need to have the stretgy generate the covering arrays
        # But, first fogure out where the covering arrays will be stored
        plan = []
        delta = datetime.timedelta(days=1)
        curr_date = start_date
        day = 1
        while curr_date <= end_date:
            ca_file = strategy_plan_dir + os.sep + 'day_' + str(day) + '_' + date_to_dir_name(curr_date) + '.ca'
            daily_plan = {'day':day, 'date':curr_date, 'ca_file':ca_file}
            plan.append(daily_plan)
            curr_date += delta
            day += 1 


        logger.info("###########################")
        
        logger.info("STRATEGY: '%s'" % strategy_name)
        logger.info("")
        logger.info("Generating a plan...")
        
        strategyObj.generate_plan(sut, plan, strategy_plan_dir)

        logger.info("Executing the plan...")        
        
        for day in plan:
            order = day['day']
            date = day['date']
            ca_file = day['ca_file']
            logger.info("   Strategy: '%s', Day:#%d (%s)" % (strategy_name, order, str(date)))

            if not os.path.isfile(ca_file):
                logger.fatal("FATAL: CA file '%s' does not exist. Exiting..." % ca_file)
                sys.exit(-1)

            # read the covering array
            ca = []
            with open(ca_file, 'r') as f:
                for cfg in f:
                    
                    cfg = cfg.strip().split(',')
                    ca.append(cfg)
 
            # execute the build
            daily_build(sut, date, ca, sut_archive_dir, strategy_archive_id)


        logger.info("Harvesting all the data for the strategy in use...")
        os_sep = os.sep 
        archive_root_dir = sut_archive_dir + os_sep + os_sep.join(strategy_archive_id)
        
        # Harvest all, added by Hanefi
        daily_builds_dir = archive_root_dir + os.sep + 'daily_builds'
        harvest_all = {}
        for day_dir_name in os.listdir(daily_builds_dir):
            harvest_daily = json.load(open(os.sep.join([daily_builds_dir, day_dir_name, "harvest_daily.json"])))
            harvest_all[day_dir_name] = harvest_daily
        
        harvest_all_file = archive_root_dir +  os.sep + 'harvest_all.json'        
        print_to_file(json.dumps(harvest_all, indent=2), harvest_all_file) 
        return True


class XYZStrategy (DailyBuildStrategy):

    def __init__(self, args):
        self.args = args
        self.name = 'XYZStrategy'
        # check the validity of the args
        # we expect to see two t1 and t2
        if ('t1' not in args) or ('t2' not in args):
            logger.fatal("FATAL: XYZ strategy expects to have 't1' and 't2' as args.")

    def args_to_dir_name(self):
        return "t1_%s_t2_%s" % (str(self.args['t1']), str(self.args['t2']))

    def generate_plan(self, sut, plan, strategy_plan_dir):

        # get the strategy arguments
        t1 = self.args['t1']
        t2 = self.args['t2']

        # get the configurations space model
        config_space_model = sut.get_config_space_model().get_model()
        
        day_cnt = len(plan)
        cas = []
        for day in plan:
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
 
            logger.info("     Generating a covering array for day %d..." % order)
            logger.info("        Output file: '%s'" % ca_out_file)

            ca_size = 2
            ca = []
            for c in range(ca_size):
                cfg = []
                for opt in config_space_model['options']:
                    randomized_settings = copy.deepcopy(opt['settings'])
                    random.shuffle(randomized_settings)
                    cfg.append(randomized_settings[0])
                ca.append(cfg)
            cas.append(ca)
         
        cas = self.priotrize_plan(cas, sut.get_config_space_model(), 
                            t2, strategy_plan_dir)   
        caidx = -1
        for day in plan:
            caidx += 1
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            ca = cas[caidx]  
            with open(ca_out_file, 'w') as ca_file:
                for cfg in ca:
                    cfg_str = ''
                    for setting in cfg:
                        cfg_str += setting 
                    ca_file.write(cfg_str + "\n")

        return None

class best_of_n_random (DailyBuildStrategy):

    def __init__(self, args):
        self.args = args
        self.name = 'best_of_n_random'
        # check the validity of the args
        # we expect to see two t1 and t2
        if ('t1' not in args) or ('t2' not in args):
            logger.fatal("FATAL: best_of_n_random strategy expects to have 't1' and 't2' as args.")

    def args_to_dir_name(self):
        return "t1_%s_t2_%s" % (str(self.args['t1']), str(self.args['t2']))
    
    def get_list_for_prioritize(self,alist,input_file):
        in_file=open(input_file,"r")
        for line in in_file:
            alist.append(line)
        in_file.close()
        return alist
    def create_last_temp_file(self,jennydict,temp_doc):
        f=open(temp_doc,"w+")
        size=len(jennydict)
        bad_chars=[",","'","[","]"]
        for x in range(size):
            line=str(jennydict[x])
            for char in bad_chars:
                line=line.replace(char,"")
            f.write(line+"\n")
        f.close()


    def convert_format(self,inputtxt,outputtxt,config_space_modell):
        in_file=open(inputtxt,"r")
        out_file=open(outputtxt,"w")
        bad_chars=[",","'","[","]"]
        for line in in_file:
            opt_count=0
            line_list=line.split()
            final_line=""
            for opt in config_space_modell['options']:
                opt_count=opt_count+1
                settings=str(opt["settings"])
                settings_list=settings.split(",")
                current_word=line_list[opt_count-1]
                current_word=str(current_word)
                current_word=current_word.replace(str(opt_count),"")
                number=ord(current_word)-97
                setting=settings_list[number]
                for char in bad_chars:
                    setting=setting.replace(char,"")
                final_line=final_line+setting+","
            final_line = final_line.rstrip(',')
            final_line=final_line.replace(" ","")  
            out_file.write(final_line)  
            out_file.write("\n")
        in_file.close()
        out_file.close()   

        
    def total_valid_tuple_count(self,paramList, t):
	    count = 0
	    for paramComb in combinations(paramList.keys(), t):
		    values = []
		    for par in paramComb:
			    values.append(paramList[par])
		    for valueComb in product(*values):
			    count += 1
	    return count
    def current_covered_tupples(self,jennydict,current,comb):
        for i in jennydict:
            list_temp=jennydict[i]
            list_temp1=tuple(combinations(jennydict[i],comb))
            for j in list_temp1:
                a = list(j)
                if current.count(a) == 0:
                    current.append(a)
        return len(current)
    
    def parse_input(self,inputfile,inputdict):
        f=open(inputfile , 'r')
        line = f.readline()
        for line in f:
            if line=="\n":
                break;
            line=line.rstrip()
            line1=line.split(':')
            line=line1[1].split(',')
            inputdict[line1[0]] = line
        f.close()
        return inputdict
    def parse_output(self,outputfile,jennydict):
        f=open(outputfile , 'r')
        count = 0
        for line in f:
            line=line.split()
            jennydict[count] = line
            count=count+1
        f.close()   
        return jennydict
    def run_jenny(self,inputfile,outputfile,t):
        jennyseed = random.randint(0 , 100000)
        f=open(inputfile,'r')
        line = f.readline()
        line = str(t)+" " + line
        command ="./jenny -n%s -s%d &> %s" % (line , jennyseed ,outputfile)
        to_run=open("run_jenny.txt","w")
        a=[]
        f.close()
        
        for word in command.split():
            a.append(str(word))
        for word2 in a:
            to_run.write(word2+" ")
        to_run.close()
        run_cmd(["bash","run_jenny.txt"])
        
        
        
        
        return None
    def create_jenny_format(self,config_space_modell,infile):
        out_file=open(infile,"w")
        characters_to_remove = "[]'" #chracters that will be removed from settings
        
                
        for opt2 in config_space_modell["options"]:
            settings2=str(opt2["settings"])
            parameter_no=settings2.count(",")+1
            out_file.write(str(parameter_no)+" ")
        out_file.write("\n") 
        for opt in config_space_modell['options']:
            option=str(opt["option"])
            out_file.write(option)
            settings=str(opt["settings"])
            
            
            for char in characters_to_remove: #remove forbidden from settings
                settings=settings.replace(char,"")
            
            
            out_file.write(": ")
            out_file.write(settings)
            out_file.write("\n")
        
        
        out_file.write("\n")
        out_file.close()
        return None   
    def generate_plan(self, sut, plan, strategy_plan_dir):

        # get the strategy arguments
        t1 = self.args['t1']
        t2 = self.args['t2']
        
        
        # get the configurations space model
        config_space_model = sut.get_config_space_model().get_model()
        run_cmd(["cp","./jenny",strategy_plan_dir])
        current_dir = os.getcwd()
        os.chdir(strategy_plan_dir)
        
        day_cnt = len(plan)
        
        number_of_arrays=1 #number of arrays
        
        
        input_dict={}
        
        all_table=[]
        
        self.create_jenny_format(config_space_model,"input.txt")
        cas=[]
        self.parse_input("input.txt",input_dict)
        totaltupple= self.total_valid_tuple_count(input_dict , t2)        
        
        for day in plan:
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            logger.info("     Generating a covering array for day %d..." % order)
            logger.info("        Output file: '%s'" % ca_out_file)
            
            most_new_array=0
            for array in range(number_of_arrays):                
                temp_dict={}
                temp_table=all_table
                self.run_jenny("input.txt" ,"output.txt",t1)
                self.parse_output("output.txt",temp_dict)
                no_covered_by_temp=self.current_covered_tupples(temp_dict,temp_table,t2)
                if no_covered_by_temp>most_new_array:
                    most_new_array=no_covered_by_temp
                    jennydict=temp_dict
                    all_table=temp_table
            self.create_last_temp_file(jennydict,"temp.txt")
            self.convert_format("temp.txt","for_priotirize.txt",config_space_model)
            daily_cas=[]
            daily_cas=self.get_list_for_prioritize(daily_cas,"for_priotirize.txt")
            cas.append(daily_cas)

        
        cas = self.priotrize_plan(cas, sut.get_config_space_model(), 
                            t2, strategy_plan_dir) 
        caidx=-1       
        for day in plan:
            caidx += 1
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            ca = cas[caidx]  
            with open(ca_out_file, 'w') as ca_file:
                for cfg in ca:
                    cfg_str = ''
                    for setting in cfg:
                        cfg_str += setting
                    cfg_str = re.sub('\,$', '', cfg_str)
                    ca_file.write(cfg_str + "\n")

        return None
        
class simple_portion_of_m_way (DailyBuildStrategy):

    def __init__(self, args):
        self.args = args
        self.name = 'simple_portion_of_m_way'
        # check the validity of the args
        # we expect to see two t1 and t2
        if ('t1' not in args) or ('t2' not in args):
            logger.fatal("FATAL: simple_portion_of_m_way strategy expects to have 't1' and 't2' as args.")

    def args_to_dir_name(self):
        return "t1_%s_t2_%s" % (str(self.args['t1']), str(self.args['t2']))
    
    def get_list_for_prioritize(self,alist,input_file):
        in_file=open(input_file,"r")
        for line in in_file:
            alist.append(line)
        in_file.close()
        return alist
    def write_to_final_cafile(self,in_file,out_file):
        infile=open(in_file,"r")
        outfile=open(out_file,"w")
        for x in range(7):
            infile.readline()
        for line in infile:
            outfile.write(line)
        infile.close()
        outfile.close()
        return None
    def give_seed(self,inputt,alist):
        f = open(inputt ,"a")
        for x in alist:
            f.write(x)
        f.close()
        return None
    
    def take_covering_array_portion(self,daily_no,outputt,alist,ignore):
        f = open(outputt)
        lock=False
        for x in range(7+ignore):
            f.readline()
        if(daily_no==-1):
            daily_no=5
            lock=True
            
        for y in range(daily_no):
            if(lock):
                daily_no=daily_no+1
            line=f.readline()
            if not line:
                break;
            alist.append(line)
        f.close()
        return alist
    
    def get_size_of_the_results(self,in_file):
        f = open(in_file,"r")
        size =-7
        while True:
            line=f.readline()
            size=size+1
            if not line:
                break;
        return size
        
    def run_acts(self,t,in_file,out_file):
        coverage="-Ddoi="+str(t)
        run_cmd(["java" ,coverage,"-Dmode=extend","-Doutput=csv","-jar","acts_3.2.jar",in_file,out_file])
        return None
    
    def create_acts_format(self,config_space_modell,infile):
        out_file=open(infile,"w")
        characters_to_remove = "[]'" #chracters that will be removed from settings
        characters_to_remove2 = "-."# characters that will be removed from options (acts doesnt allow those chars might need more for other suts)
        
        out_file.write("[System] \nName: X \n \n[Parameter]\n\n")
        
        
        for opt in config_space_modell['options']:
            option=str(opt["option"])#part we remove forbidden chars from option names
            option=option.replace("-","___")
            option=option.replace(".","____")
            out_file.write(option)
            settings=str(opt["settings"])
            
            
            for char in characters_to_remove: #remove forbidden from settings
                settings=settings.replace(char,"")
            
            if(settings.find("true")!=-1 or settings.find("TRUE")!=-1): #decide wheter it is boolean or enum 
                out_file.write(" (boolean) "+": ")
            elif(settings.isdigit()):
                out_file.write(" (int) "+": ")
            else:
                out_file.write(" (enum) "+": ")
            out_file.write(settings)
            out_file.write("\n")
        
        out_file.write("[Relation]\n\n") 
        out_file.write("[Constraint]\n\n")
        for cons in config_space_modell['constraints']:
            cons_str=str(cons)
            remove_char=["[",'"',"'","]",","]
            for char in remove_char:
                cons_str=cons_str.replace(char," ")
            count=-1
            cons_str=cons_str.replace("-","___")
            cons_str=cons_str.replace(".","____")
            cons_list=cons_str.split()
            final_string=""
            for word in cons_list:
                count=count+1
                if(count==0):
                    final_string=word+" = "
                elif(count==1):
                    if(word.isdigit()==True or word=="true" or word=="false"):
                        final_string= final_string + word +" => "
                    else:
                        final_string=final_string+'"'+word+'"'+" => "
                elif(count==2):
                    final_string=final_string+word+" != "
                else:
                    if(word.isdigit()==True or word=="true" or word=="false"):
                        final_string= final_string + word 
                    else:
                        final_string=final_string+'"'+word+'"'
            out_file.write(final_string+"\n")
            
           

               
        out_file.write("[Test Set]\n")
        test_set_parameters=""
        
        for opt in config_space_modell["options"]:
            test_set_parameters=test_set_parameters+str(opt["option"])+","
        
        test_set_parameters = test_set_parameters.rstrip(',')
        test_set_parameters=test_set_parameters.replace("-","___")
        test_set_parameters=test_set_parameters.replace(".","____")
        out_file.write(test_set_parameters)
        out_file.write("\n")
        out_file.close()
        return None
    def generate_plan(self, sut, plan, strategy_plan_dir):

        # get the strategy arguments
        t1 = self.args['t1']
        t2 = self.args['t2']

        # get the configurations space model
        config_space_model = sut.get_config_space_model().get_model() 
        run_cmd(["cp","/home/atakan/atakan/dailyBuildCaFramework/acts_3.2.jar",strategy_plan_dir]) #copy acts into strategy directory
        
        current_dir = os.getcwd()
        os.chdir(strategy_plan_dir) #go to the strategy directory
        self.create_acts_format(config_space_model,"inputfile.txt") #create a file called inputfile.txt from acts format
        self.run_acts(t2,"inputfile.txt","output.txt") #build the desired m-way (m>n)
        daily_cas=[]
        size=self.get_size_of_the_results("output.txt")#get the number of test cases needed
        day_cnt = len(plan)
        ignore=0
        daily_number=10 #number of cases to be taken from m-way
        cas=[]
        for day in plan:
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            logger.info("     Generating a covering array for day %d..." % order)
            logger.info("        Output file: '%s'" % ca_out_file)
            daily_ca_list=[]
            
            self.take_covering_array_portion(daily_number,"output.txt",daily_ca_list,ignore)
            ignore=ignore+daily_number
            self.create_acts_format(config_space_model,"daily_input.txt")
            self.give_seed("daily_input.txt",daily_ca_list)
            self.run_acts(t1,"daily_input.txt","daily_output.txt")
            
            self.write_to_final_cafile("daily_output.txt","for_priotirize.txt")     
            daily_cas=[]
            daily_cas=self.get_list_for_prioritize(daily_cas,"for_priotirize.txt")
            cas.append(daily_cas)
            if(ignore>size):
                print("coverage got")
                ignore=0        
                self.run_acts(t2,"inputfile.txt","output.txt") #build the desired m-way (m>n)        
                size=self.get_size_of_the_results("output.txt")#get the number of test cases needed
        
        cas = self.priotrize_plan(cas, sut.get_config_space_model(), 
                            t2, strategy_plan_dir) 
        caidx=-1       
        for day in plan:
            caidx += 1
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            ca = cas[caidx]  
            with open(ca_out_file, 'w') as ca_file:
                for cfg in ca:
                    cfg_str = ''
                    for setting in cfg:
                        cfg_str += setting
                    cfg_str = re.sub('\,$', '', cfg_str)
                    ca_file.write(cfg_str )
        os.chdir(current_dir)
        return None   
class updated_portion_of_m_way(DailyBuildStrategy):

    def __init__(self, args):
        self.args = args
        self.name = 'updated_portion_of_m_way'
        # check the validity of the args
        # we expect to see two t1 and t2
        if ('t1' not in args) or ('t2' not in args):
            logger.fatal("FATAL: updated_portion_of_m_way strategy expects to have 't1' and 't2' as args.")

    def args_to_dir_name(self):
        return "t1_%s_t2_%s" % (str(self.args['t1']), str(self.args['t2']))
    def get_list_for_prioritize(self,alist,input_file):
        in_file=open(input_file,"r")
        for line in in_file:
            alist.append(line)
        in_file.close()
        return alist
    def give_seed_by_file(self,infile,outfile):
        with open(infile, 'r') as f:
            for line in f:
                with open(outfile,"a")as f2:
                    f2.write(line)
        f.close()
        f2.close()
        return None
    def return_size_of_prev(self,output):
        
        count = 0
        with open(output, 'r') as f:
            for line in f:
                count += 1
        f.close
        return count

    def write_to_final_cafile(self,in_file,out_file):
        infile=open(in_file,"r")
        outfile=open(out_file,"w")
        for x in range(7):
            infile.readline()
        for line in infile:
            outfile.write(line)
        infile.close()
        outfile.close()
        return None
    def give_seed(self,inputt,alist):
        f = open(inputt ,"a+")
        for x in alist:
            f.write(x)
        f.close()
        return None
    
    def take_covering_array_portion(self,daily_no,outputt,alist,ignore):
        f = open(outputt)

        for x in range(7+ignore):
            f.readline()
       
            
        for y in range(daily_no):
            line=f.readline()
            if not line:
                break;
            alist.append(line)
        f.close()
        return None
    
    
    def get_size_of_the_results(self,in_file):
        f = open(in_file,"r")
        size =-7
        while True:
            line=f.readline()
            size=size+1
            if not line:
                break;
        f.close()
        return size
        
    def run_acts(self,t,in_file,out_file):
        coverage="-Ddoi="+str(t)
        run_cmd(["java" ,coverage,"-Dmode=extend","-Doutput=csv","-jar","acts_3.2.jar",in_file,out_file])
        
        return None
    
    def create_acts_format(self,config_space_modell,infile):
        out_file=open(infile,"w")
        characters_to_remove = "[]'" #chracters that will be removed from settings
        characters_to_remove2 = "-."# characters that will be removed from options (acts doesnt allow those chars might need more for other suts)
        
        out_file.write("[System] \nName: X \n \n[Parameter]\n\n")
        
        
        for opt in config_space_modell['options']:
            option=str(opt["option"])#part we remove forbidden chars from option names
            option=option.replace("-","___")
            option=option.replace(".","____")
            out_file.write(option)
            settings=str(opt["settings"])
            
            
            for char in characters_to_remove: #remove forbidden from settings
                settings=settings.replace(char,"")
            
            if(settings.find("true")!=-1 or settings.find("TRUE")!=-1): #decide wheter it is boolean or enum 
                out_file.write(" (boolean) "+": ")
            elif(settings.isdigit()):
                out_file.write(" (int) "+": ")
            else:
                out_file.write(" (enum) "+": ")
            out_file.write(settings)
            out_file.write("\n")
        
        out_file.write("[Relation]\n\n") 
        out_file.write("[Constraint]\n\n")
        for cons in config_space_modell['constraints']:
            cons_str=str(cons)
            remove_char=["[",'"',"'","]",","]
            for char in remove_char:
                cons_str=cons_str.replace(char," ")
            count=-1
            cons_str=cons_str.replace("-","___")
            cons_str=cons_str.replace(".","____")
            cons_list=cons_str.split()
            final_string=""
            for word in cons_list:
                count=count+1
                if(count==0):
                    final_string=word+" = "
                elif(count==1):
                    if(word.isdigit()==True or word=="true" or word=="false"):
                        final_string= final_string + word +" => "
                    else:
                        final_string=final_string+'"'+word+'"'+" => "
                elif(count==2):
                    final_string=final_string+word+" != "
                else:
                    if(word.isdigit()==True or word=="true" or word=="false"):
                        final_string= final_string + word 
                    else:
                        final_string=final_string+'"'+word+'"'
            out_file.write(final_string+"\n")
            
           

               
        out_file.write("[Test Set]\n")
        test_set_parameters=""
        
        for opt in config_space_modell["options"]:
            test_set_parameters=test_set_parameters+str(opt["option"])+","
        
        test_set_parameters = test_set_parameters.rstrip(',')
        test_set_parameters=test_set_parameters.replace("-","___")
        test_set_parameters=test_set_parameters.replace(".","____")
        out_file.write(test_set_parameters)
        out_file.write("\n")
        out_file.close()
        return None   

    
    def generate_plan(self, sut, plan, strategy_plan_dir):

        # get the strategy arguments
        t1 = self.args['t1']
        t2 = self.args['t2']
        # get the configurations space model
        config_space_model = sut.get_config_space_model().get_model() 
        run_cmd(["cp","./acts_3.2.jar",strategy_plan_dir]) #copy acts into strategy directory
        current_dir = os.getcwd()
        os.chdir(strategy_plan_dir) #go to the strategy directory
        self.create_acts_format(config_space_model,"inputfile.txt") #create a file called inputfile.txt from acts format
        
        cas=[]
        total_CA_list=[]
        size_of_prev=0
        day_cnt = len(plan)
        ignore=0
        daily_number=10 #number of cases to be taken from m-way
        for day in plan:
            daily_ca_list=[]
            daily_ca_list2=[]
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            logger.info("     Generating a covering array for day %d..." % order)
            logger.info("        Output file: '%s'" % ca_out_file)
            
            self.run_acts(t2,"inputfile.txt","outputfile.txt")
            
            if ignore>=int(self.return_size_of_prev("outputfile.txt")-7):
                self.create_acts_format(config_space_model,"inputfile.txt")
                self.run_acts(t2,"inputfile.txt","outputfile.txt")
                ignore=0
            
            
            
            self.take_covering_array_portion(daily_number,"outputfile.txt",daily_ca_list,ignore)
            self.create_acts_format(config_space_model,"daily_in.txt")
            self.give_seed("daily_in.txt",daily_ca_list)
            daily_ca_list.clear()
            self.run_acts(t1,"daily_in.txt","daily_out.txt")   
            self.take_covering_array_portion(9999,"daily_out.txt",daily_ca_list2,0)
            self.write_to_final_cafile("daily_out.txt","for_priotirize.txt")
            total_CA_list=total_CA_list+daily_ca_list2


            size_of_prev=self.return_size_of_prev("for_priotirize.txt")
            ignore=ignore+size_of_prev
            self.give_seed_by_file("for_priotirize.txt","inputfile.txt")
            daily_cas=[]
            daily_cas=self.get_list_for_prioritize(daily_cas,"for_priotirize.txt")
            cas.append(daily_cas)
        
        cas = self.priotrize_plan(cas, sut.get_config_space_model(), 
                            t2, strategy_plan_dir) 
        caidx=-1       
        for day in plan:
            caidx += 1
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            ca = cas[caidx]  
            with open(ca_out_file, 'w') as ca_file:
                for cfg in ca:
                    cfg_str = ''
                    for setting in cfg:
                        cfg_str += setting
                    cfg_str = re.sub('\,$', '', cfg_str)
                    ca_file.write(cfg_str )
        
        os.chdir(current_dir)
        return None       
# an example sut

class ABC (SUT):

    def __init__(self, config_space_model_file):
        SUT.__init__(self, "ABC", "1.0", config_space_model_file)
    
    def download(self, date_time, download_dir):
        # FIXME
        run_cmd(['git', 'clone', 'https://github.com/gabrielf/maven-samples.git', download_dir])
        # TODO implement this
        #pathlib.Path(download_dir).mkdir(parents=True, exist_ok=True)
        return True

    def configure(self, cfg, static_config_found):
        self.set_curr_config(cfg)
        self.set_static_config_found(static_config_found)
        # TODO implement this
        return True
    
    def build(self):
        # TODO implement this
        return True
    
    def run_tests(self):
        # TODO implement this
        return True

    def daily_harvest(self, in_dir):
        # TODO implement this
        return True

    def harvest_build_log(self, log_file):
        # TODO implement this        
        return {'success':True}

    def harvest_configure_log(self, log_file):
        # TODO implement this
        return {'success':True}

    def harvest_tests_log(self, log_file):
        # TODO implement this
        return {'success':True}

    def harvest_download_log(self, log_file):
        # TODO implement this
        return {'success':True}

#####

class Cassandra (SUT):
    
    def __init__(self, config_space_model_file):
        SUT.__init__(self, "Cassandra", "1.0", config_space_model_file)

    def download(self, date_time, download_dir):        
        date_time_str = date_time.strftime("%m/%d/%Y") 
        hour_str = date_time.strftime("%H:%M:%S")
        # Download Cassandra
        run_cmd(['git', 'clone', 'https://gitbox.apache.org/repos/asf/cassandra.git', download_dir])        
        # Copy checkout executable file into download_dir
        path_to_buildxml = download_dir + os.sep + "build.xml"
        if not os.path.exists(path_to_buildxml):
            return False
        shutil.copy("checkout.cassandra", download_dir)
        current_dir = os.getcwd()  # store the current dir
        os.chdir(download_dir) # go to the download dir
        run_cmd(["./checkout.cassandra", date_time_str, hour_str])
        os.chdir(current_dir) # go back to the current dir
        return True
    
    def configure(self, cfg, static_config_found):
        self.set_curr_config(cfg)
        self.set_static_config_found(static_config_found)
        #current_dir = os.getcwd() 
        working_dir = self.get_workdir()
        #os.chdir(working_dir) # go to the working dir
         
        path_to_configuration_file = working_dir + os.sep + "conf" + os.sep + "cassandra.yaml"
        path_to_configuration_file_backup = path_to_configuration_file + ".backup"        
        shutil.copy(path_to_configuration_file, path_to_configuration_file_backup)

        options = list(self.config_space_model.opt2idx.keys())
        options_seen = {option : False for option in options}
        
        in_file = open(path_to_configuration_file_backup)
        out_file = open(path_to_configuration_file, "w")
        for line in in_file:
            if line[0] not in ["\n", "#"]:
                if line.lstrip()[0] != "#":  # this is comment, skip it
                    if line[0] != " ":  # subparameter, we do not need that
                        option = line.split(":")[0]
                        out_file.write("\n")
                        if option in options_seen:
                            options_seen[option] = True
                            setting = cfg[self.config_space_model.opt2idx[option]]
                            line_cfg = option + ": " + setting + "\n"
                            out_file.write(line_cfg)
                        else:
                            out_file.write(line) 
                    else:
                        out_file.write(line)                         
        out_file.write("\n")
        in_file.close()
         
        for option in options_seen:
            if not options_seen[option]:
                setting = cfg[self.config_space_model.opt2idx[option]]
                line_cfg = option + ": " + setting + "\n\n"
                out_file.write(line_cfg) 
        out_file.close()    
        #os.chdir(current_dir)
        return True
    
    def build(self):
        current_dir = os.getcwd()  # store the current dir
        os.chdir(self.get_workdir()) # go to the working dir
        run_cmd(["ant", "build"])       
        os.chdir(current_dir) # go back to the current dir
        return True
    
    def run_tests(self):
        current_dir = os.getcwd()  # store the current dir
        os.chdir(self.get_workdir()) # go to the working dir
        #run_cmd(["ant", "test"])
        
        #ant jacoco-run -Dtaskname=testsome -Dtest.name=org.apache.cassandra.service.StorageServiceServerTest -Dtest.methods=testRegularMode,testGetAllRangesEmpty
        # To run following tests with only given methods
        
        #For debugging
        run_cmd(["ant", "jacoco-run", "-Dtaskname=testsome", 
                 "-Dtest.name=org.apache.cassandra.service.StorageServiceServerTest", 
                 "-Dtest.methods=testRegularMode,testGetAllRangesEmpty"])
        
        
        #run_cmd(["ant", "-Dmaven.test.failure.ignore=true", "jacoco-run", "test-burn"])
        
        # To generate reports
        run_cmd(["ant", "jacoco-report"])
        os.chdir(current_dir) # go back to the current dir
        return True   

    def daily_harvest(self, in_dir):
        harvest_daily = {"builds": []}
        ca = {}
        datetime = None
        for dirname in os.listdir(in_dir):
            if dirname[:3] != "cfg":  # skip other files
                continue
            path_to_cfg_harvest = os.sep.join([in_dir, dirname, "harvest.json"])
            harvest_cfg = json.load(open(path_to_cfg_harvest))
            ca[harvest_cfg["cfg_idx"]] = harvest_cfg["cfg"]
            harvest_daily["builds"].append(harvest_cfg)
            date = harvest_cfg["date"]
        harvest_daily["ca"] = ca
        harvest_daily["date"] = date
        return harvest_daily

    def harvest_all(self, in_dir):
        harvest_all = {}
        in_dir += os.sep + 'daily_builds'
        for day_dir_name in os.listdir(in_dir):
            harvest_daily = json.load(open(os.sep.join([in_dir, day_dir_name, "harvest_daily.json"])))
            harvest_all[day_dir_name] = harvest_daily
        return True

    def harvest_build_log(self, log_file):
        # test success of fail
        succ = False
        infile = open(log_file)
        for line in infile:
            if line == "BUILD SUCCESSFUL\n":  ## TODO fix this
                succ = True
                break
        infile.close()
        return {'success':succ}

    def harvest_configure_log(self, log_file):
        # TODO implement this
        return {'success':True}

    def harvest_tests_log(self, log_file):
               
        working_dir = self.get_workdir()  # current work directory
        html_content = ""
        path_to_test_results = os.sep.join([working_dir, "build", 
                                            "test", "junitreport", "all-tests.html"])    
        test_results_html = open(path_to_test_results, 'r')
        for line in test_results_html:
            html_content += line
        
        soup = BeautifulSoup(html_content, "html.parser")
    
        test_results = []
        test_results2idx = {"class": 0, "name": 1, 
                              "status": 2, "type": 3, "time": 4}
        for tr in soup.find_all('tr'):
            tds = tr.find_all('td')
            result = []
            for td in tds:
                result.append(td.text)
            test_results.append(result)
        test_results = test_results[2:]
        
        passed_count = 0
        failure_count = 0
        error_count = 0
        skipped_count = 0
        
        errors = {}
        for result in test_results:
            if result[2] == "Success":
                passed_count += 1
            elif result[2] == "Error": # find place that the error occurred
                error_count += 1
                error = result[3].split("\n")
                #error_msg_list = [e for e in error if e and not e.startswith("at") and e != "N/A"]
                error_msg_list = [e for e in error if e and e != "N/A"]
                error_msg_whole = error_msg_list[0]
                if "at" not in error_msg_whole:
                    for er in error_msg_list:
                        if "at" in er:
                            error_msg_whole = er 
                error_msg = error_msg_whole.split("at")
                error_msg = error_msg[0:2]
                error_msg = "_a_".join([e.rstrip().lstrip() for e in error_msg])
                if error_msg not in errors:
                    errors[error_msg] = []
                errors[error_msg].append({"class": result[0],
                                             "testname": result[1]})
            elif result[2] == "Fail":
                failure_count += 1
            elif result[2] == "Skipped":
                skipped_count += 1
            else:
                print("Unknown test result.")
        
        
        # analyze test results
        total_test_time = sum((float(result[test_results2idx["time"]]) for result in test_results))
        testcase_count = passed_count + failure_count + error_count + skipped_count    
   
        # read coverage results
        test_coverage = {}
        path_to_test_coverage = os.sep.join([working_dir, "build", "jacoco", "report.csv"])
        test_coverage_csv = open(path_to_test_coverage)
        attr = test_coverage_csv.readline().rstrip().split(",")
        for att in attr:
            test_coverage[att] = []
        attr_count = len(attr)
        for line in test_coverage_csv:
            line = test_coverage_csv.readline().rstrip().split(",")
            for i in range(attr_count):
                test_coverage[attr[i]].append(line[i])
        test_coverage_csv.close()
           
        # analyze coverage reports
        instruction_missed = sum((int(x) for x in test_coverage["INSTRUCTION_MISSED"]))
        instruction_covered = sum((int(x) for x in test_coverage["INSTRUCTION_COVERED"]))
        branch_missed = sum((int(x) for x in test_coverage["BRANCH_MISSED"]))
        branch_covered = sum((int(x) for x in test_coverage["BRANCH_COVERED"]))
        line_missed = sum((int(x) for x in test_coverage["LINE_MISSED"]))
        line_covered = sum((int(x) for x in test_coverage["LINE_COVERED"]))
        method_missed = sum((int(x) for x in test_coverage["METHOD_MISSED"]))
        method_covered = sum((int(x) for x in test_coverage["METHOD_COVERED"]))
        
        # TODO: need to think about when to have success fail???
        results = {"success": True,
                   "tests": {"raw": {"results": test_results, 
                                     "attribute2idx": test_results2idx },
                             "total_test_time": total_test_time,
                             "no_of_test_cases": testcase_count,
                             "test_results": {"errors": error_count,
                                              "failures": failure_count,
                                              "skipped": skipped_count,
                                              "passes": passed_count}
                            },  
                   "error_types": errors,
                   "coverage":{"raw": test_coverage,
                               "stats":{"instruction": {"missed": instruction_missed,
                                                        "covered": instruction_covered},
                                        "branch": {"missed": branch_missed,
                                                   "covered": branch_covered},
                                        "line"  : {"missed": line_missed,
                                                   "covered": line_covered},
                                        "method": {"missed": method_missed,
                                                   "covered": method_covered} 
                                        }
                               }
                   }

        return results

    def harvest_download_log(self, log_file):
        # How to understand whether download is failed from log_file?
        return {'success': True}
#known problem : while copying acts i give it a hard coded path for sometime it can crash using ./
class Flink (SUT):
    def __init__(self, config_space_model_file):
        SUT.__init__(self, "Flink", "1.0", config_space_model_file)
    
    def download(self, date_time, download_dir):        
        date_time_str = date_time.strftime("%m/%d/%Y") 
        hour_str = date_time.strftime("%H:%M:%S")
        # Download Cassandra
        run_cmd(['git', 'clone', 'https://github.com/apache/flink.git', download_dir])        
        path_to_pomxml = download_dir + os.sep + "pom.xml"
        if not os.path.exists(path_to_pomxml):
            return False
        shutil.copy("./checkout.flink",download_dir)
        current_dir = os.getcwd()  # store the current dir
        os.chdir(download_dir) # go to the download dir
        #chmod u+x checkout.flink
        run_cmd(["./checkout.flink", date_time_str, hour_str])
        os.chdir(current_dir) # go back to the current dir  
        return True
   
    def configure(self, cfg, static_config_found):
        self.set_curr_config(cfg)
        self.set_static_config_found(static_config_found)
        
        current_dir = os.getcwd()         
        working_dir = self.get_workdir()
        #run_cmd(["cp","./pom.xml.copy",working_dir])
        os.chdir(working_dir) # go to the working di
        
        pom=working_dir+os.sep+"pom.xml"
        pom_copy=pom+".copy"
        shutil.copy(pom, pom_copy)
        jacoco5="""<forkedProcessTimeoutInSeconds>3000</forkedProcessTimeoutInSeconds>
                       <forkedProcessExitTimeoutInSeconds>3000</forkedProcessExitTimeoutInSeconds>
                      <parallelTestsTimeoutInSeconds>3000</parallelTestsTimeoutInSeconds>
                    <parallelTestsTimeoutForcedInSeconds>3000</parallelTestsTimeoutForcedInSeconds> """
        #-Dmvn.surefire.timeout=1 
        jacoco3="<argLine>-Xms256m -Xmx2048m -Dmvn.forkNumber=${surefire.forkNumber"
        jacoco4="} -XX:+UseG1GC ${jacoco-coverage}</argLine>"
        in_file1=open(pom_copy,"r")
        out_file1=open(pom,"w")
        count=0
        #[67,71,72,79,83,85,89] -- original
        module_line=["<module>flink-quickstart</module>"]
        jococo="""<plugin>
<groupId>org.jacoco</groupId>
<artifactId>jacoco-maven-plugin</artifactId>
<version>0.8.2</version>
<configuration>
<destfile>${project.build.directory}/target/jacoco.exec</destfile>
</configuration>
<executions>
<!--  MODIFIED BY HANEFI  -->
<execution>
<id>default-prepare-agent</id>
<goals>
<goal>prepare-agent</goal>
</goals>
<configuration>
<propertyName>jacoco-coverage</propertyName>
</configuration>
</execution>
<execution>
<id>report</id>
<phase>test</phase>
<goals>
<goal>report</goal>
</goals>
</execution>
</executions>
</plugin>"""
        for line in in_file1:
            count=count+1
            if line.find("surefire for unit")!=-1:
                out_file1.write(jococo)
            elif line.find("<trimStackTrace>")!=-1:
                out_file1.write(line)    
                out_file1.write(jacoco5)
            elif line.find("-Dmvn.forkNumber=$")!=-1:
                out_file1.write(jacoco3+jacoco4)    
            elif (line in module_line)==False:
                out_file1.write(line)
            
            
                
        path_to_configuration_file = working_dir + os.sep + "flink-dist" + os.sep + "src" +os.sep + "main"+os.sep+"resources"+os.sep+"flink-conf.yaml"
        options = list(self.config_space_model.opt2idx.keys())
        
        
        out_file = open(path_to_configuration_file, "w")
        out_file.write("jobmanager.rpc.address: localhost \n")
        out_file.write("jobmanager.rpc.port: 6123 \n")
        out_file.write("jobmanager.memory.process.size: 1600m \n")
        out_file.write("taskmanager.memory.process.size: 1728m \n")
        out_file.write("taskmanager.numberOfTaskSlots: 1 \n") 
        out_file.write("parallelism.default: 1 \n")

        for option in options:
            if(option=="web.sumbit.enable:"):
                out_file.write("jobmanager.execution.failover-strategy: region \n")
            out_file.write(str(option)+": "+str(cfg[self.config_space_model.opt2idx[option]])+"\n")        
        out_file.close()
        out_file1.close()
        in_file1.close()
        os.chdir(current_dir)
        return True
    
    def build(self):
        current_dir = os.getcwd()  # store the current dir
        os.chdir(self.get_workdir()) # go to the working dir
        run_cmd(["mvn","-fn","package","-DskipTests","-Dmaven.test.failure.ignore=true"])
        #run_cmd(["cp","./build.log","/home/atakan/atakan/dailyBuildCaFramework"])
        os.chdir(current_dir) # go back to the current dir
        return True
    def run_tests(self):
        current_dir = os.getcwd()  # store the current dir
        work_dir=self.get_workdir()
        os.chdir(work_dir) # go to the working dir
        run_cmd(["mvn","-fn","test","-Dmaven.test.failure.ignore=true"])
        
        ind=0
        run_cmd(["mkdir","DailyBuild-jacoco_exec_files"])
        path_to_destination = work_dir+os.sep+"DailyBuild-jacoco_exec_files"
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                if file.endswith("jacoco.exec"):
                    jacoco_new_name="jacoco-"+str(ind)+".exec"
                    ind=ind+1
                    shutil.copy(os.path.join(root, file), path_to_destination+os.sep+jacoco_new_name)
        
        
        ind1=0
        run_cmd(["mkdir","DailyBuild-class_files"])
        path_to_destination2 =  work_dir+os.sep+"DailyBuild-class_files"
        class_names=[]
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                class_name="example"+str(ind1)+".class"
                ind1=ind1+1
                if file.endswith(".class"):
                    shutil.copy(os.path.join(root, file), path_to_destination2+os.sep+class_name)
        
        
        jacocoli_path="/home/atakan/atakan/dailyBuildCaFramework/jacoco-0.8.5/lib/jacococli.jar"   
        merge_list=["java","-jar",jacocoli_path,"merge"]
    
        for a in range(ind):
            jacoco_new_name="jacoco-"+str(a)+".exec"
            merge_list.append(jacoco_new_name)
        merge_list.append("--destfile")
        merge_list.append("jacoco-merged.exec")
        os.chdir(work_dir+os.sep+"DailyBuild-jacoco_exec_files")
        run_cmd(merge_list)
       
        #below is hard coded path but it should work once the paths are changed
        #run_cmd(["java","-jar","/home/atakan/atakan/dailyBuildCaFramework/jacoco-0.8.5/lib/jacococli.jar","report","/home/atakan/atakan/dailyBuildCaFramework/Flink/work/DailyBuild-jacoco_exec_files/jacoco-merged.exec","--classfiles","/home/atakan/atakan/dailyBuildCaFramework/Flink/work/DailyBuild-jacoco_exec_files/DailyBuild-class_files/","--csv","results.csv"])
        
        os.chdir(current_dir) # go back to the current dir
        return True
    
    def daily_harvest(self, in_dir):
        
        
        return True

    def harvest_all(self, in_dir):
        
        return True

    def harvest_build_log(self, log_file):
        #TODO FIX
        return {'success':True}

    def harvest_configure_log(self, log_file):
        # TODO implement this
        return {'success':True}

    def harvest_tests_log(self, log_file):
               

        return {'success':True}

    def harvest_download_log(self, log_file):
        # How to understand whether download is failed from log_file?
        return {'success': True}

#there are hardcoded paths
sut = 'Flink'
config_space_model_file = '/home/atakan/atakan/dailyBuildCaFramework/flink.model.txt'
start_date = datetime.datetime(2020, 6, 1, 23, 55, 0) # jan 1, 2020 at 23:55:00
end_date = datetime.datetime(2020, 6, 3, 23, 55, 0) # jan 3, 2020 at 23:55:00
archive_dir = '/home/atakan/atakan/dailyBuildCaFramework'

strategies = [{'name':'simple_portion_of_m_way', 'args':{'t1': 2, 't2':3}}]

run_experiment(sut, config_space_model_file,
               start_date, end_date,
               strategies,
               archive_dir)

# TODO:
# in build.xml file search for
#    Read all answers from here: https://stackoverflow.com/a/16690564
#    failonerror
#    maxmemory 
#    jvmarg

