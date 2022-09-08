from . import mongoConnector
from . import mongokit

#connector = mongoConnector.MongoConnector()
mongokit_connector = mongokit.connection

__all__ = ['mongokit_connector']
__all__ += mongoConnector.__all__
__all__ += mongokit.__all__
