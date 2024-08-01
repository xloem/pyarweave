DEFAULT_MU_HOST = 'https://mu.ao-testnet.xyz'
DEFAULT_CU_HOST = 'https://cu.ao-testnet.xyz'

# made of DataItems with tags Data-Protocol and Type=Process or Type=Message
# ao/servers/su/src/domain/core/flows.rs

from .cu import ComputeUnit
from .mu import MessengerUnit
from .su import SchedulerUnit

cu = ComputeUnit
mu = MessengerUnit
su = SchedulerUnit

AR_IO_TESTNET_PROCESS_ID = 'agYcCFJtrMG6cqMuZfskIkFTGvUPddICmtQSBIoPdiA'
