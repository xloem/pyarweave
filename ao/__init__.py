#DEFAULT_MU_HOST = 'https://mu.ao-testnet.xyz'
#DEFAULT_CU_HOST = 'https://cu.ao-testnet.xyz'
DEFAULT_CU_HOST = 'https://cu.ardrive.io'

# made of DataItems with tags Data-Protocol and Type=Process or Type=Message
# ao/servers/su/src/domain/core/flows.rs

from .cu import ComputeUnit
#from .mu import MessengerUnit
from .su import SchedulerUnit

cu = ComputeUnit
#mu = MessengerUnit
su = SchedulerUnit

# ar-io-sdk/src/constants.ts

AR_IO_DEVNET_PROCESS_ID = 'GaQrvEMKBpkjofgnBi_B3IgIDmY_XYelVLB6GcRGrHc'
AR_IO_TESTNET_PROCESS_ID = 'agYcCFJtrMG6cqMuZfskIkFTGvUPddICmtQSBIoPdiA'
AR_IO_MAINNET_PROCESS_ID = 'qNvAoz0TgcH7DMg8BCVn8jF32QH5L6T29VjHxhHqqGE'
