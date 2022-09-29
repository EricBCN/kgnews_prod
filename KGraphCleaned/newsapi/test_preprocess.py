from utils.mongoConnector import mongo_connector
import utils.mongokit as mongokit
import datetime

if __name__ == "__main__":
    # mongo_connector.insert_id(123)
    # delete news after "2022-09-01"
    # query = {
    #     "published_at": {
    #         "$gte": datetime.datetime.strptime("2022-09-01", "%Y-%m-%d")
    #     }
    # }
    #
    # mongo_connector.delete_many(query)

    # set entity []
    mongokit.set_entity_empty()


