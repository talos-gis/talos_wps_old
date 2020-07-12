from .wps_info import GetInfo
from .wps_sayhello import SayHello
from .wps_sleep import Sleep
from .wps_ls import ls
from .jsonprocess import TestJson

from .wps_crop_color import GdalDem
from .wps_rasval import RasterValue
from .wps_invert import Invert
from .wps_viewshed import ViewShed
from .wps_calc import Calc

from .buffer import Buffer

# For the process list on the home page
processes = [
    GetInfo(),
    SayHello(),
    Sleep(),
    ls(),
    TestJson(),

    GdalDem(),
    RasterValue(),
    Invert(),
    ViewShed(),
    Calc(),

    Buffer(),
]

# For the process list on the home page

process_descriptor = {}
for process in processes:
    abstract = process.abstract
    identifier = process.identifier
    process_descriptor[identifier] = abstract

