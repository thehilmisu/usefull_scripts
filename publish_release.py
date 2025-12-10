#!/usr/bin/env python3

'''
@file publish_release.py
@brief: This script is used to create a release by automatically:
- Increment the Variant number in system_settings.h version
- Commit the change in system_settings
- Create a Tag for this current version and push the tag to origin

Notes: 
- This script will fail if there are uncomitted changes in the current repo.
- if the script fails, the repo is revereted to where it was before the script.

TODO:
- fill in the system settings info and print it in the release
- Add firmware size infomration

'''
import re
import os
import sys
import pathlib
import shutil
import datetime 
from argparse import ArgumentParser, RawTextHelpFormatter
from gitobj import GitObj
import subprocess
from check_compiler_version import get_compiler_version
from rename import get_full_filename, h2py_get_filename, get_file_path

def get_root_path():
    """
    Get the root folder absolute path, use it as a base for all paths
    """
    return pathlib.Path(os.path.realpath(__file__)).parents[1]

sys.path.append(str(get_root_path() / 'scripts'))
from h2py import h2py

SRC_DIR = str(get_root_path() / 'code' / 'src')

NVRAM_CLEAR_FILENMAE = '8133x_eeprom_cust_cleared.hex'
SYSTEM_SETTING_PY_PATH = str(get_root_path() / 'code' / 'src' / 'system_settings.py')
SYSTEM_SETTING_PATH = str(get_root_path() / 'code' / 'src' / 'system_settings.h')
SYSTEM_SETTING_BACKUP_PATH = str(get_root_path() / 'code' / 'src' / 'system_settings_backup.h')

CURRENT_LIMIT_PATH = str(get_root_path() / 'code' / 'src' / 'current_limit.h')
CURRENT_LIMIT_PY_PATH = str(get_root_path() / 'code' / 'src' / 'current_limit.py')

GIT_COMMIT_MSG_PATH = str(get_root_path() / 'code' / 'src' / '.gitcommitmsg.txt')
BUILD_BAT_PATH = str(get_root_path() / 'build.bat')
RELEASES_DIR_PATH = get_root_path() / 'release'
MAKEFILE_CONF_PATH = str(get_root_path() / 'code' / 'src' / 'Makefile.configure.mk')
NVRAM_CLEAR_FILE_PATH = str(get_root_path() / 'code' / 'src' / NVRAM_CLEAR_FILENMAE)

SYSTEM_SETTING_RELATIVE_PATH = 'code/src/system_settings.h'
GIT_COMMIT_MSG_RELATIVE_PATH = 'code/src/.gitcommitmsg.txt'
GIT_DEVELOP_BRANCH_NAME = 'develop'
GIT_MASTER_BRANCH_NAME = 'master'

# Define the regex patterns
# We opted for 3 groups, to keep the spaces unchanged.
# group(1) : the first part starting from #define to the opening bracket
# group(2) : the actual variable to edit inside bracket
# group(3) : the last part starting the closing bracket to the end of line

YEAR_RE_PATTERN    = r'(#define SOFTWARE_VERSION_YEAR\s+\()(.*)(\)\s*)'
WEEK_RE_PATTERN    = r'(#define SOFTWARE_VERSION_WEEK\s+\()(.*)(\)\s*)'
LEVEL_RE_PATTERN   = r'(#define SOFTWARE_VERSION_LEVEL\s+\()(.*)(\)\s*)'
VARIANT_RE_PATTERN = r'(#define SOFTWARE_VERSION_VARIANT\s+\()(.*)(\)\s*)'

HELP_TEXT ="""
Script to update the version in system_settings.h
Example
python update_version.py
"""

LEVEL_NON_VALIDATED = 0x00
LEVEL_VALIDATED     = 0x01

class ReleaseObj:
    pass

def parse_args():
    """Parse command line arguments"""
    pars = ArgumentParser(formatter_class=RawTextHelpFormatter, epilog=HELP_TEXT)

    pars.add_argument(
        '-d', '--no-date-update',
        help='disable updating the year and the current week',
        action="store_true",
        default=False)

    pars.add_argument(
        '-v', '--no-variant-inc',
        help='disable incrementing the variant',
        action="store_true",
        default=False)
    
    pars.add_argument(
        '-l', '--update-level',
        help='Update the Level to 1 for validated projects',
        action="store_true",
        default=False)
    
    pars.add_argument(
        '-b', '--branch',
        help='the branch to checkout to or stay in for applying the changes and tags',
        type=str,
        default=GIT_DEVELOP_BRANCH_NAME)
    
    return pars.parse_args()

def build_code():
    try:
        output = subprocess.Popen(['build.bat'],
                                cwd=get_root_path(),
                                stderr=subprocess.STDOUT,
                                stdout=subprocess.PIPE,
                                shell=True)
        for line in output.stdout:
            print(line.decode().strip())

        ret = output.wait()

        if ret == 0:
            print("Build success!")
        else:
            raise IOError(f"Build.bat failure. firmware compilation Failed!")



    except subprocess.CalledProcessError as e:
        raise IOError(f"Command failed with return code {e.returncode}, Msg: {e.output.decode()}")
    
def update_version():
    args = parse_args()

    # Define the regular expressions to match the #define statements
    year_regex    = re.compile(YEAR_RE_PATTERN)
    week_regex    = re.compile(WEEK_RE_PATTERN)
    level_regex   = re.compile(LEVEL_RE_PATTERN)
    variant_regex = re.compile(VARIANT_RE_PATTERN)

    # Create a Backup file
    shutil.copy(SYSTEM_SETTING_PATH, SYSTEM_SETTING_BACKUP_PATH)

    # Read the input file
    with open(SYSTEM_SETTING_PATH, 'r') as f:
        input_text = f.read()

    # Extract the values of the version as strings
    old_year_value    = year_regex.search(input_text).group(2)
    old_week_value    = week_regex.search(input_text).group(2)
    old_level_value   = level_regex.search(input_text).group(2)
    old_variant_value = variant_regex.search(input_text).group(2)

    # Edit the version

    if args.no_date_update:
        new_year_value  = int(old_year_value, 0)
        new_week_value  = int(old_week_value, 0)
    else:
        # No change
        today = datetime.date.today()
        new_year_value = int(today.strftime('%y'))
        new_week_value = int(today.strftime('%V'))
    
    # if args.update_level:
    #     new_level_value = LEVEL_VALIDATED
    # else:
    #     # No change
    #     new_level_value = int(old_level_value, 0)

    new_level_value = int(old_level_value, 0)

    if args.no_variant_inc:
        # Increment the value of variant
        new_variant_value = int(old_variant_value, 0)
    else:
        # No change
        new_variant_value = int(old_variant_value, 0) + 1

    # Modify the #define statements using the regular expressions
    output_text = year_regex.sub(f'\\g<1>0x{new_year_value:02X}\\g<3>', input_text)
    output_text = week_regex.sub(f'\\g<1>0x{new_week_value:02X}\\g<3>', output_text)
    output_text = level_regex.sub( f'\\g<1>0x{new_level_value:02X}\\g<3>', output_text)
    output_text = variant_regex.sub(f'\\g<1>0x{new_variant_value:02X}\\g<3>', output_text)

    # Write the modified output to a new file
    with open(SYSTEM_SETTING_PATH, 'w') as f:
        f.write(output_text)
    
    return f'v{new_level_value}.{new_variant_value:03}'

def get_mlx_memory_size():
    mem_size = ReleaseObj()

    mem_size.total_flash = 32 #kB
    mem_size.total_ram   = 2  #kB

    try:
        # git diff stats only to make parsing easy.
        output = subprocess.check_output(["mlx16-size", "-A", f"{get_full_filename()}.elf"],
                                            cwd=get_root_path(),
                                            stderr=subprocess.STDOUT,
                                            shell=True)
        output = output.decode("utf-8")

    except subprocess.CalledProcessError as e:
        raise IOError(f"Command failed with return code {e.returncode}, Msg: {e.output.decode()}")

    mem_size.empty_flash = 0
    mem_size.used_ram   = 0

    for line in output.splitlines():
        if '.flash_fill' in line:
            mem_size.empty_flash = int(line.split()[1])
        elif '.dp' in line:
            mem_size.used_ram = mem_size.used_ram + int(line.split()[1])
        elif '.data' in line:
            mem_size.used_ram = mem_size.used_ram + int(line.split()[1])
        elif '.bss' in line:
            mem_size.used_ram = mem_size.used_ram + int(line.split()[1])

    mem_size.empty_flash = round(mem_size.empty_flash / 1024, 2)
    mem_size.used_flash = round(mem_size.total_flash - mem_size.empty_flash, 2)
    
    mem_size.used_flash_per = round(mem_size.used_flash *100 / mem_size.total_flash, 2)
    mem_size.empty_flash_per = round(mem_size.empty_flash *100 / mem_size.total_flash, 2)
    
    mem_size.used_ram = round(mem_size.used_ram / 1024, 2)
    mem_size.empty_ram = round(mem_size.total_ram - mem_size.used_ram, 2)

    mem_size.empty_ram_per = round(mem_size.empty_ram * 100 / mem_size.total_ram, 2)
    mem_size.used_ram_per = round(mem_size.used_ram * 100 / mem_size.total_ram, 2)

    return mem_size

def get_system_settings_info():
    h2py(SYSTEM_SETTING_PATH, SYSTEM_SETTING_PY_PATH, quiet=True)
    d = {}
    exec(rf'sys.path.append(r"{SRC_DIR}")')
    exec('import system_settings', d)
    os.remove(SYSTEM_SETTING_PY_PATH)

    ss_info                  = ReleaseObj()
    ss_info.hw_number        = f'{d["system_settings"].HARDWARE_VERSION_NUMBER}'
    ss_info.hw_sample_status = f'{d["system_settings"].HARDWARE_SAMPLE_STATUS}'
    ss_info.ov_set           = f'{d["system_settings"].VOLTAGE_HIGH_SET}'
    ss_info.ov_clear         = f'{d["system_settings"].VOLTAGE_HIGH_CLR}'
    ss_info.uv_set           = f'{d["system_settings"].VOLTAGE_LOW_SET}'
    ss_info.uv_clear         = f'{d["system_settings"].VOLTAGE_LOW_CLR}'
    ss_info.ot_set           = f'{d["system_settings"].TEMPERATURE_HIGH_SET}'
    ss_info.ot_clear         = f'{d["system_settings"].TEMPERATURE_HIGH_CLR}'
    ss_info.gear_ratio       = f'{d["system_settings"].GEAR_RATIO}'
    ss_info.stall_offset     = f'{d["system_settings"].STALL_OFFSET_ANGLE}'
    ss_info.nominal_angle    = f'{d["system_settings"].ACTUATOR_MOVEMENT_ANGLE}'
    ss_info.max_angle        = f'{d["system_settings"].MAX_CALIBMOVE_ANGLE}'
    ss_info.min_angle        = f'{d["system_settings"].MIN_CALIBMOVE_ANGLE}'
    ss_info.abused_mode      = d["system_settings"].ABUSED_FUNCTION
    try:
        ss_info.open_dir     = d["system_settings"].OPEN_DIRECTION
    except:
        print("/!\\Warning: Open direction setting is not defined")
        ss_info.open_dir     = 0
    try:    
        ss_info.sleep_mode   = d["system_settings"].SLEEP_MODE_ENABLED
    except:
        print("/!\\Warning: Sleep mode setting is not defined")
        ss_info.sleep_mode   = 0
    

    return ss_info 


def get_current_limit_info():
    h2py(CURRENT_LIMIT_PATH, CURRENT_LIMIT_PY_PATH, quiet=True)
    d = {}
    exec(rf'sys.path.append(r"{SRC_DIR}")')
    exec('import current_limit', d)

    cl_info                                                    = ReleaseObj()

    cl_info.CURRENT_LIMIT_MA_OVER85C_LOW_MODE                       = f'{d["current_limit"].CURRENT_LIMIT_MA_OVER85C_LOW_MODE}'
    cl_info.CURRENT_LIMIT_MA_40C_85C_LOW_MODE                       = f'{d["current_limit"].CURRENT_LIMIT_MA_40C_85C_LOW_MODE}'
    cl_info.CURRENT_LIMIT_MA_23C_40C_LOW_MODE                       = f'{d["current_limit"].CURRENT_LIMIT_MA_23C_40C_LOW_MODE}'
    cl_info.CURRENT_LIMIT_MA_0C_23C_LOW_MODE                        = f'{d["current_limit"].CURRENT_LIMIT_MA_0C_23C_LOW_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE20C_0C_LOW_MODE                = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE20C_0C_LOW_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_LOW_MODE       = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_LOW_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_LOW_MODE       = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_LOW_MODE}'
    cl_info.CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_LOW_MODE             = f'{d["current_limit"].CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_LOW_MODE}'
    cl_info.CURRENT_LIMIT_MA_OVER85C_MID_MODE                       = f'{d["current_limit"].CURRENT_LIMIT_MA_OVER85C_MID_MODE}'
    cl_info.CURRENT_LIMIT_MA_40C_85C_MID_MODE                       = f'{d["current_limit"].CURRENT_LIMIT_MA_40C_85C_MID_MODE}'
    cl_info.CURRENT_LIMIT_MA_23C_40C_MID_MODE                       = f'{d["current_limit"].CURRENT_LIMIT_MA_23C_40C_MID_MODE}'
    cl_info.CURRENT_LIMIT_MA_0C_23C_MID_MODE                        = f'{d["current_limit"].CURRENT_LIMIT_MA_0C_23C_MID_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE20C_0C_MID_MODE                = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE20C_0C_MID_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_MID_MODE       = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_MID_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_MID_MODE       = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_MID_MODE}'
    cl_info.CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_MID_MODE             = f'{d["current_limit"].CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_MID_MODE}'
    cl_info.CURRENT_LIMIT_MA_OVER85C_HIGH_MODE                      = f'{d["current_limit"].CURRENT_LIMIT_MA_OVER85C_HIGH_MODE}'
    cl_info.CURRENT_LIMIT_MA_40C_85C_HIGH_MODE                      = f'{d["current_limit"].CURRENT_LIMIT_MA_40C_85C_HIGH_MODE}'
    cl_info.CURRENT_LIMIT_MA_23C_40C_HIGH_MODE                      = f'{d["current_limit"].CURRENT_LIMIT_MA_23C_40C_HIGH_MODE}'
    cl_info.CURRENT_LIMIT_MA_0C_23C_HIGH_MODE                       = f'{d["current_limit"].CURRENT_LIMIT_MA_0C_23C_HIGH_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE20C_0C_HIGH_MODE               = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE20C_0C_HIGH_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_HIGH_MODE      = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_HIGH_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_HIGH_MODE      = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_HIGH_MODE}'
    cl_info.CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_HIGH_MODE            = f'{d["current_limit"].CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_HIGH_MODE}'
    cl_info.CURRENT_LIMIT_MA_OVER85C_DEF_MODE                       = f'{d["current_limit"].CURRENT_LIMIT_MA_OVER85C_DEF_MODE}'
    cl_info.CURRENT_LIMIT_MA_40C_85C_DEF_MODE                       = f'{d["current_limit"].CURRENT_LIMIT_MA_40C_85C_DEF_MODE}'
    cl_info.CURRENT_LIMIT_MA_23C_40C_DEF_MODE                       = f'{d["current_limit"].CURRENT_LIMIT_MA_23C_40C_DEF_MODE}'
    cl_info.CURRENT_LIMIT_MA_0C_23C_DEF_MODE                        = f'{d["current_limit"].CURRENT_LIMIT_MA_0C_23C_DEF_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE20C_0C_DEF_MODE                = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE20C_0C_DEF_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_DEF_MODE       = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_DEF_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_DEF_MODE       = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_DEF_MODE}'
    cl_info.CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_DEF_MODE             = f'{d["current_limit"].CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_DEF_MODE}'

    cl_info.CURRENT_LIMIT_MA_OVER85C_BOOST_MODE                   = f'{d["current_limit"].CURRENT_LIMIT_MA_OVER85C_BOOST_MODE}'
    cl_info.CURRENT_LIMIT_MA_40C_85C_BOOST_MODE                   = f'{d["current_limit"].CURRENT_LIMIT_MA_40C_85C_BOOST_MODE}'
    cl_info.CURRENT_LIMIT_MA_23C_40C_BOOST_MODE                   = f'{d["current_limit"].CURRENT_LIMIT_MA_23C_40C_BOOST_MODE}'
    cl_info.CURRENT_LIMIT_MA_0C_23C_BOOST_MODE                    = f'{d["current_limit"].CURRENT_LIMIT_MA_0C_23C_BOOST_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE20C_0C_BOOST_MODE            = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE20C_0C_BOOST_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_BOOST_MODE   = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_BOOST_MODE}'
    cl_info.CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_BOOST_MODE   = f'{d["current_limit"].CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_BOOST_MODE}'
    cl_info.CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_BOOST_MODE         = f'{d["current_limit"].CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_BOOST_MODE}'

    os.remove(CURRENT_LIMIT_PY_PATH)

    return cl_info 

def get_release_note_txt(release_obj):
    ss_info = get_system_settings_info()
    cl_info = get_current_limit_info()
    mem_size = get_mlx_memory_size()
    release_txt = f'''# Release Note:
    
## Release Info:

- **Project Name** : {release_obj.proj_name}
- **Version** : {release_obj.fw_version}
- **MCi Version** : {release_obj.mci_version}
- **Chip** : {release_obj.chip_name}

- **Date** : {release_obj.timestamp}
- **Author** : {release_obj.author}

## Release Description : {release_obj.title}

{release_obj.body}

## Release content:

- Firmware Hexfile : {release_obj.hexfile}
- Empty NVRAM file: {NVRAM_CLEAR_FILENMAE}
- Init NVRAM Hex File : {release_obj.nvm_init_hex}
- Init NVRAM Config File : {release_obj.nvm_init_json}
- This release note
- 

## Features supported in this release

/!\ Fill in Manually /!\ newly added features that are relevent and did not exist in previous release)

## Features Not supported in this release

/!\ Fill in Manually /!\ Features that should have been added but couldn't be added for some reasons)

## Anomalies Found during Testing

/!\ Fill in Manually /!\ bugs that must be reported, found during testing)

## Bugs Fixed in this release

/!\ Fill in Manually /!\ bugs that existed prior to this release and are fixed in this release.)

## System Settings

HARDWARE_VERSION_NUMBER   = {ss_info.hw_number}.{ss_info.hw_sample_status}\n
VOLTAGE_HIGH_SET          = {ss_info.ov_set}
VOLTAGE_HIGH_CLR          = {ss_info.ov_clear}
VOLTAGE_LOW_SET           = {ss_info.uv_set}
VOLTAGE_LOW_CLR           = {ss_info.uv_clear}\n
TEMPERATURE_HIGH_SET      = {ss_info.ot_set}
TEMPERATURE_HIGH_CLR      = {ss_info.ot_clear}\n
GEAR_RATIO              = {ss_info.gear_ratio}\n
STALL_OFFSET_ANGLE      = {ss_info.stall_offset}\n
ACTUATOR_MOVEMENT_ANGLE = {ss_info.nominal_angle}
MAX_CALIBMOVE_ANGLE     = {ss_info.max_angle}
MIN_CALIBMOVE_ANGLE     = {ss_info.min_angle}\n
ABUSED_FUNCTION           = {"ON" if ss_info.abused_mode == 1 else "OFF"}\n
OPEN_DIRECTION            = {"CCW" if ss_info.open_dir == 1 else "CW"}\n
SLEEP_MODE_ENABLED        = {"TRUE" if ss_info.sleep_mode == 1 else "FALSE"}\n

APP_DEBUGGING             = {"TRUE" if release_obj.debugging_enabled == 1 else "FALSE"}\n

# Current limits Info

## LOW SPEED

CURRENT_LIMIT_MA_OVER85C_LOW_MODE                    = {cl_info.CURRENT_LIMIT_MA_OVER85C_LOW_MODE}
CURRENT_LIMIT_MA_40C_85C_LOW_MODE                    = {cl_info.CURRENT_LIMIT_MA_40C_85C_LOW_MODE}
CURRENT_LIMIT_MA_23C_40C_LOW_MODE                    = {cl_info.CURRENT_LIMIT_MA_23C_40C_LOW_MODE}
CURRENT_LIMIT_MA_0C_23C_LOW_MODE                     = {cl_info.CURRENT_LIMIT_MA_0C_23C_LOW_MODE}
CURRENT_LIMIT_MA_NEGATIVE20C_0C_LOW_MODE             = {cl_info.CURRENT_LIMIT_MA_NEGATIVE20C_0C_LOW_MODE}
CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_LOW_MODE    = {cl_info.CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_LOW_MODE}
CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_LOW_MODE    = {cl_info.CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_LOW_MODE}
CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_LOW_MODE          = {cl_info.CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_LOW_MODE}

## MID SPEED

CURRENT_LIMIT_MA_OVER85C_MID_MODE                    = {cl_info.CURRENT_LIMIT_MA_OVER85C_MID_MODE}
CURRENT_LIMIT_MA_40C_85C_MID_MODE                    = {cl_info.CURRENT_LIMIT_MA_40C_85C_MID_MODE}
CURRENT_LIMIT_MA_23C_40C_MID_MODE                    = {cl_info.CURRENT_LIMIT_MA_23C_40C_MID_MODE}
CURRENT_LIMIT_MA_0C_23C_MID_MODE                     = {cl_info.CURRENT_LIMIT_MA_0C_23C_MID_MODE}
CURRENT_LIMIT_MA_NEGATIVE20C_0C_MID_MODE             = {cl_info.CURRENT_LIMIT_MA_NEGATIVE20C_0C_MID_MODE}
CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_MID_MODE    = {cl_info.CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_MID_MODE}
CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_MID_MODE    = {cl_info.CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_MID_MODE}
CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_MID_MODE          = {cl_info.CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_MID_MODE}

## HIGH SPEED

CURRENT_LIMIT_MA_OVER85C_HIGH_MODE                   = {cl_info.CURRENT_LIMIT_MA_OVER85C_HIGH_MODE}
CURRENT_LIMIT_MA_40C_85C_HIGH_MODE                   = {cl_info.CURRENT_LIMIT_MA_40C_85C_HIGH_MODE}
CURRENT_LIMIT_MA_23C_40C_HIGH_MODE                   = {cl_info.CURRENT_LIMIT_MA_23C_40C_HIGH_MODE}
CURRENT_LIMIT_MA_0C_23C_HIGH_MODE                    = {cl_info.CURRENT_LIMIT_MA_0C_23C_HIGH_MODE}
CURRENT_LIMIT_MA_NEGATIVE20C_0C_HIGH_MODE            = {cl_info.CURRENT_LIMIT_MA_NEGATIVE20C_0C_HIGH_MODE}
CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_HIGH_MODE = {cl_info.CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_HIGH_MODE}
CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_HIGH_MODE = {cl_info.CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_HIGH_MODE}
CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_HIGH_MODE         = {cl_info.CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_HIGH_MODE}

## DEFAULT SPEED 

CURRENT_LIMIT_MA_OVER85C_DEF_MODE                    = {cl_info.CURRENT_LIMIT_MA_OVER85C_DEF_MODE}
CURRENT_LIMIT_MA_40C_85C_DEF_MODE                    = {cl_info.CURRENT_LIMIT_MA_40C_85C_DEF_MODE}
CURRENT_LIMIT_MA_23C_40C_DEF_MODE                    = {cl_info.CURRENT_LIMIT_MA_23C_40C_DEF_MODE}
CURRENT_LIMIT_MA_0C_23C_DEF_MODE                     = {cl_info.CURRENT_LIMIT_MA_0C_23C_DEF_MODE}
CURRENT_LIMIT_MA_NEGATIVE20C_0C_DEF_MODE             = {cl_info.CURRENT_LIMIT_MA_NEGATIVE20C_0C_DEF_MODE}
CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_DEF_MODE    = {cl_info.CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_DEF_MODE}
CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_DEF_MODE    = {cl_info.CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_DEF_MODE}
CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_DEF_MODE          = {cl_info.CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_DEF_MODE}

## BOOST MODE

CURRENT_LIMIT_MA_OVER85C_BOOST_MODE                   = {cl_info.CURRENT_LIMIT_MA_OVER85C_BOOST_MODE}
CURRENT_LIMIT_MA_40C_85C_BOOST_MODE                   = {cl_info.CURRENT_LIMIT_MA_40C_85C_BOOST_MODE}
CURRENT_LIMIT_MA_23C_40C_BOOST_MODE                   = {cl_info.CURRENT_LIMIT_MA_23C_40C_BOOST_MODE}
CURRENT_LIMIT_MA_0C_23C_BOOST_MODE                    = {cl_info.CURRENT_LIMIT_MA_0C_23C_BOOST_MODE}
CURRENT_LIMIT_MA_NEGATIVE20C_0C_BOOST_MODE            = {cl_info.CURRENT_LIMIT_MA_NEGATIVE20C_0C_BOOST_MODE}
CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_BOOST_MODE   = {cl_info.CURRENT_LIMIT_MA_NEGATIVE30C_NEGATIVE20C_BOOST_MODE}
CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_BOOST_MODE   = {cl_info.CURRENT_LIMIT_MA_NEGATIVE40C_NEGATIVE30C_BOOST_MODE}
CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_BOOST_MODE         = {cl_info.CURRENT_LIMIT_MA_UNDER_NEGATIVE40C_BOOST_MODE}

## Memory Size Info

- Flash
    Total : {mem_size.total_flash:.2f} kB, Used: {mem_size.used_flash:.2f} kB ({mem_size.used_flash_per:.2f} %), empty {mem_size.empty_flash:.2f} kB ({mem_size.empty_flash_per:.2f} %)

- RAM
    Total : {mem_size.total_ram:.2f} kB, Used: {mem_size.used_ram:.2f} kB ({mem_size.used_ram_per:.2f} %), empty {mem_size.empty_ram:.2f} kB ({mem_size.empty_ram_per:.2f} %)

## Source Code info

- Compiler : {release_obj.compiler}
- Source code remote location: {release_obj.source_path}
- Source code remote branch : {release_obj.branch}
- Release commit hash: {release_obj.commit_hash}
'''
    return release_txt

def create_release(release_obj):
    now = datetime.datetime.now()
    timestamp = now.strftime("%d-%b-%y_%H-%M-%S")

    release_folder = RELEASES_DIR_PATH / timestamp

    if not release_folder.exists():
        try:
            release_folder.mkdir(parents=False)
        except Exception as e:
            raise IOError(f"Parent Folder {RELEASES_DIR_PATH} Does not exsist. Error {str(e)}")
    else:
        raise IOError(f"Folder {release_folder} already exsist!")

    release_note_filename = pathlib.Path("release_note_" + release_obj.fw_version + ".txt")

    release_note_path = release_folder / release_note_filename
    release_obj.timestamp = timestamp
    release_obj.nvm_init_hex = f"{h2py_get_filename().split('_')[0]}_{h2py_get_filename().split('_')[1]}_NVM_init_file.hex"
    release_obj.nvm_init_json = f"{h2py_get_filename().split('_')[0]}_{h2py_get_filename().split('_')[1]}_NVM_init_file.json"
    note_text = get_release_note_txt(release_obj)

    # Create the release note txt
    with open(release_note_path, 'w') as f:
        f.write(note_text)
    
    #Copy the hexfile to the release folder
    hex_file_path = pathlib.Path(f"{get_full_filename()}.hex")
    release_hex_path = release_folder / f"{h2py_get_filename()}{'_DEBUG' if release_obj.debugging_enabled == 1 else ''}.hex"
    empty_nvm_release_path = release_folder / NVRAM_CLEAR_FILENMAE

    # Get the init NVRAM files
    init_hex_nvm_path = f"{get_file_path()}/{release_obj.nvm_init_hex}"
    init_json_nvm_path = f"{get_file_path()}/{release_obj.nvm_init_json}"

    init_nvm_hex_release_path = release_folder/ f"{release_obj.nvm_init_hex}"
    init_nvm_json_release_path = release_folder / f"{release_obj.nvm_init_json}"

    shutil.copy(hex_file_path, release_hex_path)
    shutil.copy(NVRAM_CLEAR_FILE_PATH, empty_nvm_release_path)
    shutil.copy(init_hex_nvm_path, init_nvm_hex_release_path)
    shutil.copy(init_json_nvm_path, init_nvm_json_release_path)
    
    print(f"Release Folder {release_folder} created Successfuly!")

def publish_version(git):
    # Store current head to return to in case of an error.
    reset_git_hash = git.get_commit_hash()
    
    try:
        # No Other changes are in the repo, update the version
        version_tag = update_version()
        if git.curr_branch != GIT_DEVELOP_BRANCH_NAME:
            version_tag = version_tag + '@' + git.get_commit_hash()[:6]

        tag_is_set = False
        changes = git.parse_diff()
        print(len(changes))
        if len(changes) == 0:
            # No changes
            print("/!\ Warning: System settings has not been edited.")

        
        elif len(changes) == 1:
            # Only one file changed
            # Double check for safety that changes are only made in system settings
            # and that all changes are modifications, additions == deletions
            # there is a maximum of four modifications for the four version numbers
            print(changes[0]['filename'] == SYSTEM_SETTING_RELATIVE_PATH)
            print("--------------------------------------------------------")
            print(0 < changes[0]['added']) 
            print(changes[0]['added'])
            print(changes[0]['deleted'] <= 4)
            print(changes[0]['deleted'])
            if changes[0]['filename'] == SYSTEM_SETTING_RELATIVE_PATH and 0 < changes[0]['added'] :
                
                print(f"Version Number set to : {version_tag}")

                commit_title = input("Commit Title: ")
                commit_body = input('Commit Body: (Brief description of the release)')

                msg = f'Release {version_tag}: {commit_title}\n\n{commit_body}'

                # to be able to use return carriage in the text we commit using a file of a message
                with open(GIT_COMMIT_MSG_PATH, 'w') as f:
                    f.write(msg)

                # Commit system_settings update of the version
                git.commit(SYSTEM_SETTING_RELATIVE_PATH, commit_msgfile=GIT_COMMIT_MSG_RELATIVE_PATH)

                # delete the commit file message once the changes are commited
                try:
                    os.remove(GIT_COMMIT_MSG_PATH)
                except FileNotFoundError:
                    print("Warning: commit message file not found")

                # Build the source code before publishing
                build_code()

                # Create a tag with the version number to trace back the releases
                git.tag(version_tag)
                tag_is_set = True

                print("Pushing the code to remote origin...")
                # publish the release so that everyone has access to it.
                git.push()

                # publish the tag
                git.tag_push(version_tag)

                print(f"\nBranch {git.curr_branch} and tag {version_tag} successfully pushed to origin.")

            else:
                raise IOError("System settings diff shows unexpected changes. wrong file or more changes than it should", changes)

        else:
            raise IOError("More than one files changed. Changes: ", changes)
    except Exception as e:
        print("Failed: Resting repo to previous state to {reset_git_hash}")
        git.reset_hard(reset_git_hash)

        if tag_is_set:
            git.tag_delete(version_tag, delete_remote=True)

        raise IOError(f"Exception Occured, Msg: {str(e)}")

    return (version_tag, commit_title, commit_body)

def main():
    # Get the Makefile config and check Debugging enabled or not.
    with open(MAKEFILE_CONF_PATH, 'r') as f:
        makefile_config_text = f.read()

    debugging_enabled = 0

    git = GitObj(get_root_path())

    # Check the current branch
    if git.curr_branch != GIT_DEVELOP_BRANCH_NAME:
        print(f"/!\ Warning: you are releasing from {git.curr_branch} branch, which is different from Dev Branch {GIT_DEVELOP_BRANCH_NAME}")
        print("Press Enter to continue or Ctrl+C to quit...")
        try:
            while True:
                key = input()
                if key == "":
                    break
                
        except KeyboardInterrupt:
            print("Interrupted! Exiting...")
            exit()

    # check if there is no uncommited changes
    if len(git.get_uncomitted_changes()) > 1:
        raise IOError("Commit your changes before running update version script")
    
    # Checkout to develop branch (Not necessary)
    #git.checkout(args.branch)

    # Return commit description
    #commit_desc = ('v.9.999', 'title', 'body')
    commit_desc = publish_version(git)

    # Create a release folder
    print("Creating release folder...")
    # Get the remote link for the source code
    if re.search(r"^ssh://git@", git.get_remote_url()) is not None:
        # if MCI bitbucket is used SSH link is used
        match = re.search(r"^ssh://git@(.*?)/(.*?)/(.*?)\.git$", git.get_remote_url())
    elif re.search(r"^git@", git.get_remote_url()) is not None:
        # if SSH link is used
        match = re.search(r"^git@(.*?):(.*?)/(.*?)\.git$", git.get_remote_url())
    else:
        # if HTTPS link is used
        match = re.search(r"^https://.*@(.*?)/(.*?)/(.*?)\.git$", git.get_remote_url())
    
    website = match.group(1)
    workspace = match.group(2)
    project = match.group(3)

    # Recreate a a vlid link for the origin
    website_url = f"https://{website}/{workspace}/{project}"

    # Fill in the release obj to print it in Release Note.
    release_obj             = ReleaseObj()
    release_obj.fw_version  = commit_desc[0]
    release_obj.proj_name   = project
    release_obj.chip_name   = 'MLX_81332' # to be set later
    release_obj.author      = git.get_author()
    release_obj.title       = commit_desc[1]
    release_obj.body        = commit_desc[2]
    release_obj.compiler    = get_compiler_version().split('\n')[0].strip()
    release_obj.commit_hash = git.get_commit_hash()
    release_obj.source_path = website_url
    release_obj.branch      = git.curr_branch
    release_obj.hexfile     = f"{h2py_get_filename()}.hex"
    release_obj.mci_version = f"{h2py_get_filename()}".replace('_','.')
    release_obj.debugging_enabled = debugging_enabled

    # Set the chip name
    match = re.search(r'PRODUCT\s*\?\=\s*(.*)\s*', makefile_config_text)
    if match:
        release_obj.chip_name   = 'MLX_' + match.group(1)
    
    # Create the release folder
    create_release(release_obj)

if __name__ == '__main__':
    main()
