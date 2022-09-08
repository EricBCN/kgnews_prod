
class InternalServerError(Exception):
    pass

class SchemaValidationError(Exception):
    pass

class WrongFormatFields(Exception):
    pass


errors = {
    "InternalServerError": {
        "message": "Something went wrong",
        "status": 500
    },
    "SchemaValidationError": {
        "message": "Request is missing required fields",
        "status": 400
    },
    "WrongFormatFields": {
        "message": "Invalid argument format",
        "status": 400
    }
}