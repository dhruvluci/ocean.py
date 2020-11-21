#! ./venv/bin/python3

import glob
import json
import re
import os
import shutil
import subprocess
import sys

print('===Begin make.py')

print('===Check Python version')
s = subprocess.check_output('python --version', shell=True)  # eg 'Python 2.7.17'
version = float(re.findall(' \d\.[\d|\d\d]', str(s))[0])  # eg 2.7
if version < 3.6:
    print('===Need >= Python 3.6')
    sys.exit(0)

print('===Check virtualenv')
if 'venv' not in str(os.environ.get('VIRTUAL_ENV')):
    print("""
Virtual environment not running. Have you done these? 
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt""")
    sys.exit(0)

if not os.path.exists('/tmp/contracts'):
    print('===  Clone contracts')
    os.system('cd /tmp; git clone https://github.com/oceanprotocol/contracts; git checkout 7a48ca50c14f9117bc808c997585f071fb4285b3; cd -')
    # don't need to ever update them, since it's an old version
# else:
#     print('===  Update contracts')
#     os.system('cd /tmp/contracts; git pull; cd -')

if not os.path.exists('/tmp/openzeppelin-contracts'):  # note that we use v0.2.5
    print('===  Clone openzeppelin-contracts')
    os.system('cd /tmp; git clone --branch v2.5.0 https://github.com/OpenZeppelin/openzeppelin-contracts.git; cd -')
    # don't need to ever update them, since it's an old version
    
print('===Clone/update .sol sources: done')

SUBDIRS = ['build', 'contracts', 'interfaces', 'reports', 'scripts']#no 'tests'
print(f'===Initialize brownie dirs {SUBDIRS} (but keep tests/):')
#Let 'brownie init' do the work, and preserve 'tests/'  
TEMP_BROWNIE_DIR = '/tmp/brownie_dir'
for subdir in SUBDIRS: #kill old subdirs
    os.system(f'rm -rf {subdir}')
os.system(f'rm -rf {TEMP_BROWNIE_DIR}')
os.system(f'brownie init {TEMP_BROWNIE_DIR}')
for subdir in SUBDIRS:
    os.system(f'mv {TEMP_BROWNIE_DIR}/{subdir} .') #move in new version
os.system(f'rm -rf {TEMP_BROWNIE_DIR}')
CONTRACTDIR = './contracts'
BUILDDIR = './build'
NEW_CONTRACTDIR = './new_contracts' #contracts this repo, vs other repos

print(f'===Populate {CONTRACTDIR}')
os.system(f'cp /tmp/contracts/contracts/*.sol {CONTRACTDIR}')
os.system(f'cp /tmp/contracts/contracts/*/*.sol {CONTRACTDIR}')

os.system(f'cp /tmp/openzeppelin-contracts/contracts/ownership/Ownable.sol {CONTRACTDIR}/')
os.system(f'cp /tmp/openzeppelin-contracts/contracts/token/ERC20/ERC20.sol {CONTRACTDIR}/')
os.system(f'cp /tmp/openzeppelin-contracts/contracts/token/ERC20/../../GSN/Context.sol {CONTRACTDIR}/')
#os.system(f'cp /tmp/openzeppelin-contracts/contracts/token/ERC20/./IERC20.sol {CONTRACTDIR}') #use BToken
os.system(f'cp /tmp/openzeppelin-contracts/contracts/token/ERC20/../../math/SafeMath.sol {CONTRACTDIR}')
os.system(f'cp /tmp/openzeppelin-contracts/contracts/token/ERC20/../../utils/Address.sol {CONTRACTDIR}')

os.system(f'cp {NEW_CONTRACTDIR}/BToken.sol {CONTRACTDIR}')

#----------------------
print('===In-place change .sol files: flatten imports, more')

def inplace_change(filename, old_s, new_s):
    with open(filename) as f:
        s = f.read()
        if old_s not in s:
            return
    with open(filename, 'w') as f:
        s = s.replace(old_s, new_s)
        f.write(s)
    
#Fix imports
for f in glob.glob(f'{CONTRACTDIR}/*.sol'):
    inplace_change(f, 'IERC20.sol', 'BToken.sol')
    inplace_change(f, 'solidity 0.5.7', 'solidity <0.6.0')
    inplace_change(f, 'solidity 0.5.12', 'solidity <0.6.0')
    inplace_change(f, 'solidity >= 0.4.22 <0.7.0', 'solidity <0.6.0')
    inplace_change(f, 'openzeppelin-solidity/contracts/', './')
    inplace_change(f, '../../', './')
    inplace_change(f, '../', './')
    inplace_change(f, 'fee/', '')
    inplace_change(f, 'GSN/', '')
    inplace_change(f, 'math/', '')
    inplace_change(f, 'token/', '')
    inplace_change(f, 'utils/', '')
    inplace_change(f, 'ERC20/', '')
    inplace_change(f, 'interfaces/', '')
    inplace_change(f, 'ownership/', '')

print('===Compile')
os.system(f'cd {CONTRACTDIR}; brownie compile; cd -')

print('===Update abi/')
# these are needed for ocean_lib/Ocean.py to be independent of brownie
for module in ['DataTokenTemplate', 'DTFactory', \
               'BFactory', 'BPool', 'BToken']: 
    with open(f'{BUILDDIR}/contracts/{module}.json', 'r') as f:
        json_dict = json.loads(f.read())
    with open(f'abi/{module}.abi', 'w') as f:
        f.write(json.dumps(json_dict['abi'], indent=4))

print('===Done!')
