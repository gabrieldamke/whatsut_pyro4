import customtkinter as ctk
import Pyro4
import threading
from tkinter import messagebox, simpledialog
import logging

# Configuração do logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@Pyro4.expose
class ClientCallback:
    def __init__(self, client):
        self.client = client

    def update(self, change_type):
        logging.debug(f"Callback received: {change_type}")
        self.client.refresh_lists()

    def new_message(self, sender, recipient, message):
        logging.debug(f"New message received: {sender} -> {recipient}: {message}")
        self.client.receive_message(sender, recipient, message)

class WhatsUTClient:
    def __init__(self, master):
        self.master = master
        self.master.title("WhatsUT")
        self.master.geometry("800x600")
        
        ctk.set_appearance_mode("System")  # Modo escuro/claro automático
        ctk.set_default_color_theme("blue")  # Tema de cor
        
        self.server = Pyro4.Proxy("PYRONAME:whatsut.server")
        
        # Tela de login
        self.login_frame = ctk.CTkFrame(master, corner_radius=10)
        self.login_frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        self.username_label = ctk.CTkLabel(self.login_frame, text="Username:")
        self.username_label.pack(pady=10)
        self.username_entry = ctk.CTkEntry(self.login_frame)
        self.username_entry.pack(pady=10)
        
        self.password_label = ctk.CTkLabel(self.login_frame, text="Password:")
        self.password_label.pack(pady=10)
        self.password_entry = ctk.CTkEntry(self.login_frame, show="*")
        self.password_entry.pack(pady=10)
        
        self.login_button = ctk.CTkButton(self.login_frame, text="Login", command=self.login)
        self.login_button.pack(pady=10)
        self.register_button = ctk.CTkButton(self.login_frame, text="Register", command=self.register)
        self.register_button.pack(pady=10)
        
        # Tela principal
        self.main_frame = ctk.CTkFrame(master, corner_radius=10)
        
        self.sidebar_frame = ctk.CTkFrame(self.main_frame, width=200, corner_radius=10)
        self.sidebar_frame.pack(side="left", fill="y", padx=(0, 20), pady=10)

        self.chat_frame = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.chat_frame.pack(side="right", fill="both", expand=True, pady=10)
        
        # Sidebar com contatos e grupos
        self.search_entry = ctk.CTkEntry(self.sidebar_frame, placeholder_text="Search")
        self.search_entry.pack(pady=10, fill="x")
        self.search_entry.bind("<KeyRelease>", self.filter_contacts_and_groups)
        
        self.user_list_label = ctk.CTkLabel(self.sidebar_frame, text="User List:")
        self.user_list_label.pack(pady=10, anchor="w")
        self.user_list_frame = ctk.CTkFrame(self.sidebar_frame, corner_radius=10)
        self.user_list_frame.pack(pady=10, fill="both", expand=True)
        
        self.group_list_label = ctk.CTkLabel(self.sidebar_frame, text="Group List:")
        self.group_list_label.pack(pady=10, anchor="w")
        self.group_list_frame = ctk.CTkFrame(self.sidebar_frame, corner_radius=10)
        self.group_list_frame.pack(pady=10, fill="both", expand=True)

        self.create_group_button = ctk.CTkButton(self.sidebar_frame, text="Create Group", command=self.create_group)
        self.create_group_button.pack(pady=10)
        
        # Área de chat
        self.messages_label = ctk.CTkLabel(self.chat_frame, text="Messages:")
        self.messages_label.pack(pady=10, anchor="w")
        self.messages_textbox = ctk.CTkTextbox(self.chat_frame, height=10)
        self.messages_textbox.pack(pady=10, fill="both", expand=True)

        self.message_entry = ctk.CTkEntry(self.chat_frame, placeholder_text="Enter your message")
        self.message_entry.pack(pady=10, fill="x")
        self.send_button = ctk.CTkButton(self.chat_frame, text="Send Message", command=self.send_message)
        self.send_button.pack(pady=10)

        self.selected_contact_or_group = None
        self.callback_daemon_thread = None
        self.register_callback()
    
    def register_callback(self):
        try:
            self.callback = ClientCallback(self)
            self.daemon = Pyro4.Daemon()
            self.callback_uri = self.daemon.register(self.callback)
            self.server.register_callback(self.callback_uri)
            self.callback_daemon_thread = threading.Thread(target=self.daemon_loop)
            self.callback_daemon_thread.daemon = True
            self.callback_daemon_thread.start()
            logging.debug("Callback registered successfully.")
        except Exception as e:
            logging.error(f"Error registering callback: {e}")

    def daemon_loop(self):
        try:
            self.daemon.requestLoop()
        except Exception as e:
            logging.error(f"Daemon loop error: {e}")

    def login(self):
        try:
            username = self.username_entry.get()
            password = self.password_entry.get()
            result = self.server.login(username, password)
            if result == "Login successful.":
                self.login_frame.pack_forget()
                self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)
                self.refresh_lists()
            else:
                messagebox.showerror("Error", result)
        except Exception as e:
            logging.error(f"Error during login: {e}")
            messagebox.showerror("Error", f"Error during login: {e}")
    
    def register(self):
        try:
            username = self.username_entry.get()
            password = self.password_entry.get()
            result = self.server.register_user(username, password)
            messagebox.showinfo("Info", result)
        except Exception as e:
            logging.error(f"Error during registration: {e}")
            messagebox.showerror("Error", f"Error during registration: {e}")
    
    def refresh_lists(self):
        try:
            # Atualizar lista de usuários
            for widget in self.user_list_frame.winfo_children():
                widget.destroy()
            users = self.server.get_user_list()
            for user in users:
                user_button = ctk.CTkButton(self.user_list_frame, text=user, command=lambda u=user: self.select_user(u))
                user_button.pack(pady=5, fill="x")

            # Atualizar lista de grupos
            for widget in self.group_list_frame.winfo_children():
                widget.destroy()
            groups = self.server.get_group_list()
            for group in groups:
                group_button = ctk.CTkButton(self.group_list_frame, text=group, command=lambda g=group: self.select_group(g))
                group_button.pack(pady=5, fill="x")

            if self.selected_contact_or_group:
                self.refresh_messages()
        except Exception as e:
            logging.error(f"Error refreshing lists: {e}")
    
    def filter_contacts_and_groups(self, event):
        try:
            search_text = self.search_entry.get().lower()
            
            # Filtrar lista de usuários
            for widget in self.user_list_frame.winfo_children():
                widget.destroy()
            users = self.server.get_user_list()
            for user in users:
                if search_text in user.lower():
                    user_button = ctk.CTkButton(self.user_list_frame, text=user, command=lambda u=user: self.select_user(u))
                    user_button.pack(pady=5, fill="x")
            
            # Filtrar lista de grupos
            for widget in self.group_list_frame.winfo_children():
                widget.destroy()
            groups = self.server.get_group_list()
            for group in groups:
                if search_text in group.lower():
                    group_button = ctk.CTkButton(self.group_list_frame, text=group, command=lambda g=group: self.select_group(g))
                    group_button.pack(pady=5, fill="x")
        except Exception as e:
            logging.error(f"Error filtering contacts and groups: {e}")
    
    def select_user(self, user):
        self.selected_contact_or_group = user
        self.refresh_messages()

    def select_group(self, group):
        self.selected_contact_or_group = group
        self.refresh_messages()
    
    def refresh_messages(self):
        try:
            if not self.selected_contact_or_group:
                return

            self.messages_textbox.delete("1.0", ctk.END)
            messages = self.server.get_messages(self.selected_contact_or_group)
            for message in messages:
                self.messages_textbox.insert(ctk.END, message + "\n")
        except Exception as e:
            logging.error(f"Error refreshing messages: {e}")

    def receive_message(self, sender, recipient, message):
        try:
            if self.selected_contact_or_group == recipient or self.selected_contact_or_group == sender:
                self.messages_textbox.insert(ctk.END, f"{sender}: {message}\n")
                # Auto-scroll to the end of the message box
                self.messages_textbox.see(ctk.END)
        except Exception as e:
            logging.error(f"Error receiving message: {e}")

    def send_message(self):
        try:
            if not self.selected_contact_or_group:
                messagebox.showerror("Error", "No recipient selected.")
                return

            message = self.message_entry.get()
            sender = self.username_entry.get()
            recipient = self.selected_contact_or_group
            result = self.server.send_message(sender, recipient, message)
            messagebox.showinfo("Info", result)
            self.message_entry.delete(0, ctk.END)
            self.refresh_messages()
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            messagebox.showerror("Error", f"Error sending message: {e}")

    def create_group(self):
        try:
            group_name = simpledialog.askstring("Group Name", "Enter the new group's name:")
            creator = self.username_entry.get()
            result = self.server.create_group(group_name, creator)
            messagebox.showinfo("Info", result)
            self.refresh_lists()
        except Exception as e:
            logging.error(f"Error creating group: {e}")
            messagebox.showerror("Error", f"Error creating group: {e}")

if __name__ == "__main__":
    root = ctk.CTk()
    client = WhatsUTClient(root)
    root.mainloop()