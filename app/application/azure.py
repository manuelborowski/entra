from app import flask_app
from azure.identity import ClientSecretCredential
from msgraph.core import GraphClient

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


class Graph:
    client_credential: ClientSecretCredential
    client: GraphClient

    def start(self):
        # in Azure Directory Admin center, in the App Registration, in the app (Python Graph Tutorial), in  API permissions, make sure the TYPE of the permission is Application, NOT Delegated
        #  The required permissions can be found in the API reference, e.g. https://learn.microsoft.com/en-us/graph/api/user-list?view=graph-rest-1.0&tabs=http
        if not hasattr(self, 'client_credential'):
            client_id = flask_app.config['AZURE_CLIENT_ID']
            tenant_id = flask_app.config['AZURE_TENANT_ID']
            client_secret = flask_app.config['AZURE_CLIENT_SECRET']
            self.client_credential = ClientSecretCredential(tenant_id, client_id, client_secret)

        if not hasattr(self, 'client'):
            self.client = GraphClient(credential=self.client_credential, scopes=['https://graph.microsoft.com/.default'])


    def get_computers(self, link=None):
        if link:
            request_url = link
        else:
            endpoint = '/deviceManagement/managedDevices'
            select="complianceState,managedDeviceOwnerType,deviceName,userPrincipalName"
            order_by = 'deviceName'
            request_url = f'{endpoint}?$select={select}&$orderBy={order_by}'
        response = self.client.get(request_url)
        return response.json()


# azure = Graph()
# azure.start()
# test = azure.get_computers()
# print(test)