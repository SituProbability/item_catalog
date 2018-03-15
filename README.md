# Project Item Catalog

This app lets the user log-in using google's oauth and create a topic category to store with items.
If the user is not able to login, it will only preview the basic information.

### Prerequisites
The app requires vagrant in able to run the app. You can download it from [virtualbox.org](https://www.vagrantup.com/downloads.html).
Install the platform package for your operating system. 
It also requires python 2 and pip for installing the library requirements within vagrant.
In addition, it requires to set-up Google OAuth credentials through google developer site. 

### Installing

After installing vagrant it will require to install python 2 within vagrant. 
Sometimes vagrant folder has python already installed. 

#### App Libraries
The App is dependent in the libraries listed as the following:
```
flask
httplib2
oauth2client
requests
sqlalchem
```
It can be installed using pip by typing pip install followed by the name of the package.

#### Generate and Obtain Google OAuth credentials
Google OAuth is utilize by the app in order for the user to login and it requires token credentials from Google Dev.
Go to your app's page in the Google APIs [Console](https://console.developers.google.com/apis) to create the client ID and client secret
After obtaining Google OAuth, download the client_secrets.json then make sure its embedded in the CLIENT_ID in views.py like the following:

```
CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())[
    'web']['client_id']
```
Replace the "data-clientid" in login.html with your client ID.

Test the Google OAuth if its operational by running the app ```python views.py``` then typing in the browser ```http://localhost:8000/gconnect/```.
It will redirect the user in the google plus login prompt.  

## Running the App

After making the vagrant operational and successfully installed the requirements above, download this project into the vagrant folder.
Inside project folder, type ```python views.py```. Then type in the browser ```http://localhost:8000/```,
and it will forward you to the categories page if you're not logged in; Otherwise, if you'll logged in you will see some activated menus for CRUD.


### Future Features
There are some upgrades that will make the app better, such as adding CSRF protection on CRUD operations, more third party OAuth.
