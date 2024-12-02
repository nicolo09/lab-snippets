from snippets.lab3 import Server
from snippets.lab4.users import Role, User
from snippets.lab4.users.impl import InMemoryUserDatabase
from snippets.lab4.example1_presentation import serialize, deserialize, Request, Response
from snippets.lab4.users.impl import InMemoryAuthenticationService
import traceback

ENABLE_DEBUG = True

class ServerStub(Server):
    
    DEFAULT_ADMIN = User('admin', ["admin@localhost"], 'Admin', Role.ADMIN, 'admin')
    
    def __init__(self, port):
        super().__init__(port, self.__on_connection_event)
        self.__user_db = InMemoryUserDatabase()
        self.__auth_service = InMemoryAuthenticationService(self.__user_db, debug=ENABLE_DEBUG)
        self.__user_db.add_user(self.DEFAULT_ADMIN)
    
    def __on_connection_event(self, event, connection, address, error):
        match event:
            case 'listen':
                print('Server listening on %s:%d' % address)
            case 'connect':
                connection.callback = self.__on_message_event
            case 'error':
                traceback.print_exception(error)
            case 'stop':
                print('Server stopped')
    
    def __on_message_event(self, event, payload, connection, error):
        match event:
            case 'message':
                print('[%s:%d] Open connection' % connection.remote_address)
                request = deserialize(payload)
                assert isinstance(request, Request)
                print('[%s:%d] Unmarshall request:' % connection.remote_address, request)
                response = self.__handle_request(request)
                connection.send(serialize(response))
                print('[%s:%d] Marshall response:' % connection.remote_address, response)
                connection.close()
            case 'error':
                traceback.print_exception(error)
            case 'close':
                print('[%s:%d] Close connection' % connection.remote_address)
    
    def __handle_request(self, request):
        try:
            if request.name == 'authenticate':
                # If the request is for the authentication service, call it
                method = getattr(self.__auth_service, request.name)
            else:
                # If the request is for the user database, check the authentication token
                if not request.metadata.get('token'):
                    raise ValueError("Authentication token is required")
                elif not self.__auth_service.validate_token(request.metadata['token']):
                    raise ValueError("Invalid authentication token")
                else:
                    if request.metadata['token'].user.role != Role.ADMIN:
                        raise ValueError("Insufficient privileges")                    
                    method = getattr(self.__user_db, request.name)
            result = method(*request.args)
            error = None
        except Exception as e:
            result = None
            error = " ".join(e.args)
        return Response(result, error)


if __name__ == '__main__':
    # Run on port 8080 with "poetry run python -m snippets -l 4 -e 2 8080"
    import sys
    server = ServerStub(int(sys.argv[1]))
    while True:
        try:
            input('Close server with Ctrl+D (Unix) or Ctrl+Z (Win)\n')
        except (EOFError, KeyboardInterrupt):
            break
    server.close()
