import os
import subprocess
from datetime import date

from get_root_path import get_root_path


def main():
    print('Creating version header file...')
    git_hash = subprocess.check_output('git rev-parse --short=6 HEAD', shell=True).decode('ascii').strip()
    today = date.today()

    with open(os.path.join(get_root_path(), 'code', 'src', 'internal_version.h'), 'w') as f:
        f.write(f'''#pragma once
#define GIT_COMMIT 0x{git_hash}
#define RELEASE_YEAR {today.strftime('%y')}
#define RELEASE_WEEK {today.strftime('%W')}
''')


if __name__ == '__main__':
    main()
