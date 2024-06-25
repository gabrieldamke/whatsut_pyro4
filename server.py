import Pyro4
import hashlib
from Pyro4 import expose, behavior

@expose
@behavior(instance_mode="single")
class WhatsUTServer:
    def __init__(self):
        self.users = {}  # username: password_hash
        self.logged_in_users = []
        self.groups = {}  # group_name: [members]
        self.messages = {}  # username: [messages]
        self.callbacks = []

    def register_user(self, username, password):
        if username in self.users:
            return "Username already exists."
        self.users[username] = hashlib.sha256(password.encode()).hexdigest()
        self.messages[username] = []
        self.notify_clients("user")
        return "User registered successfully."

    def login(self, username, password):
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if username in self.users and self.users[username] == password_hash:
            self.logged_in_users.append(username)
            return "Login successful."
        return "Invalid username or password."

    def get_user_list(self):
        return self.logged_in_users

    def get_group_list(self):
        return list(self.groups.keys())

    def create_group(self, group_name, creator):
        if group_name in self.groups:
            return "Group already exists."
        self.groups[group_name] = [creator]
        self.notify_clients("group")
        return "Group created successfully."

    def join_group(self, group_name, username):
        if group_name not in self.groups:
            return "Group does not exist."
        self.groups[group_name].append(username)
        return "Joined group successfully."

    def send_message(self, sender, recipient, message):
        if recipient in self.messages:
            self.messages[recipient].append(f"{sender}: {message}")
            self.notify_message(sender, recipient, message)
            return "Message sent."
        return "Recipient not found."

    def get_messages(self, username):
        if username in self.messages:
            return self.messages[username]
        return []

    def register_callback(self, callback_uri):
        callback = Pyro4.Proxy(callback_uri)
        self.callbacks.append(callback)
        return "Callback registered successfully."

    def notify_clients(self, change_type):
        for callback in self.callbacks:
            try:
                callback.update(change_type)
            except Pyro4.errors.ConnectionClosedError:
                self.callbacks.remove(callback)

    def notify_message(self, sender, recipient, message):
        for callback in self.callbacks:
            try:
                callback.new_message(sender, recipient, message)
            except Pyro4.errors.ConnectionClosedError:
                self.callbacks.remove(callback)

def start_server():
    # Conectar ao servidor de nomes
    with Pyro4.Daemon() as daemon:
        ns = Pyro4.locateNS()
        uri = daemon.register(WhatsUTServer)
        ns.register("whatsut.server", uri)

        print("Servidor WhatsUT iniciado.")
        daemon.requestLoop()

if __name__ == "__main__":
    start_server()