import pathlib
from tkinter import *
from tkinter import ttk
from tkinter import messagebox
from PIL import ImageTk, Image
from shutil import copyfile
import os
import requests
import json
import zipfile
import re
from threading import Thread
from db_module import update_db, find_name_in_db, find_path_in_db

import config

login = config.login
password = config.password
web_address = config.web_address
server_address = config.server_address

web_connection_flag = True
server_connection_flag = True

local_db_search = True


class ScrollableFrame(Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = Canvas(self, width=1130, height=660)

        self.canvas.configure(bg='black')
        self.canvas.configure(highlightcolor='black')
        self.canvas.configure(highlightbackground='black')

        self.scrollbar = Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = Frame(self.canvas)
        self.activebackground = 'black'
        self.bg = 'black'

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )

        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")



def start_session():
    s = requests.Session()
    r = s.get(f'{web_address}/SearchWeb/index.jsp')
    print(r.status_code)
    if r.status_code != 200:
        raise EXCEPTION('Web failure')
    return s


def log_in(login, password, my_session):
    data = {
        'user': login,
        'pass': password
    }
    r = my_session.get(f'{web_address}/SearchWeb/Auth', params=data)
    # if not json.loads(r.text)['auth']:
    #     show_message('Ошибка авторизации', frame_web_search)
    return r


def search_in_web(name='', designation=''):
    param = {
        'dirName': '',
        'destignatio': designation,
        'oboz_isp': '',
        'name': name,
        'patch': '',
        'd1': '2003-07-03',
        'd2': '2020-06-04',
        'from': '0',
        'to': '100'
    }
    result = my_session.get(f'{web_address}/SearchWeb/GetDocuments', params=param)
    return result


def represent_results(event=None):
    if web_connection_flag:
        Thread(target=represent_results_web_search, args=[], daemon=True).start()
        # represent_results_web_search()
    if server_connection_flag:
        # if local_db_search:
        #     pass
        # else:
        show_message('Поиск ... ', frame_local_server)
        Thread(target=represent_results_local_server, args=[], daemon=True).start()

        # represent_results_local_server()



def represent_results_web_search(event=None):
    # clears the screen before representing new result
    for widget in frame_web_search.scrollable_frame.winfo_children():
        widget.destroy()

    # move the scrollbar to the top of the search result
    frame_web_search.canvas.yview_moveto('0')

    # get message str from entry widget
    message_string = message.get()

    # switch finding info by designation or by name
    if message_string.find('.') != -1:
        result = json.loads(search_in_web(designation=message_string).text)
    else:
        result = json.loads(search_in_web(name=message_string).text)

    table = result['table']

    try:

        # print(table[0]['designatio'])

        for i in range(len(table)):
            label1 = Label(frame_web_search.scrollable_frame, text=table[i]['designatio'].strip()[:28:],
                           fg="black",
                           bg="#eee",
                           font="Helvetica 14 bold",
                           width=30,
                           bd=0,
                           borderwidth=0)
            label1.grid(row=i, column=0, padx=20, pady=10)

            label2 = Label(frame_web_search.scrollable_frame, text=table[i]['name'].strip()[:42:],
                           fg="black",
                           bg="#eee",
                           font="Helvetica 14 bold",
                           width=45,
                           anchor="w",
                           justify=LEFT,
                           bd=0)
            label2.grid(row=i, column=1, padx=20)

            btn = Button(frame_web_search.scrollable_frame, text="Скачать",  # текст кнопки
                         background="black",  # фоновый цвет кнопки
                         foreground="white",  # цвет текста
                         padx="20",  # отступ от границ до содержимого по горизонтали
                         pady="5",  # отступ от границ до содержимого по вертикали
                         font="Helvetica 12 bold",  # высота шрифта
                         command=lambda c=i: download_result_from_web(c, table)
                         )
            btn.grid(row=i, column=3, padx=20)

    except IndexError:

        show_message('По запрашиваемой строке информации в архиве нет', frame_web_search)


def download_result_from_web(i, table):
    designation = table[i]['designatio']
    name = table[i]['name']
    path = table[i]['patch'].replace('\\', '/')
    r = my_session.get(f'{web_address}/SearchWeb/GetZip?filename={path}', stream=True)

    archive_name = f'{designation} - {name}_search.zip'
    with open(archive_name, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            f.write(chunk)

    z = zipfile.ZipFile(archive_name)

    print(z.namelist())

    if not z.namelist():
        z.close()
        handle_empty_archive(archive_name)
    else:
        messagebox.showinfo('Скачивание прошло успешно', f'Скачан архив {archive_name}')


def handle_empty_archive(file_name):
    messagebox.showinfo("Ошибка", "Запрашиваемый архив не содержит никаких файлов")
    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), file_name)
    os.remove(path)


def represent_results_local_server(event=None):
    # clears the screen before representing new result
    for widget in frame_local_server.scrollable_frame.winfo_children():
        widget.destroy()

    # move the scrollbar to the top of the search result
    frame_local_server.canvas.yview_moveto('0')

    # get message str from entry widget
    message_string = message.get().lower()

    paths = []
    table = []

    if local_db_search:
        paths = find_path_in_db(message_string)
        table = find_name_in_db(message_string)
    else:

        for roots, dirs, files in os.walk(f"{server_address}"):
            for file in files:

                if re.search(message_string, file.lower()):
                    table.append(file)
                    print(os.path.join(roots, file))
                    paths.append(os.path.join(roots, file))

    max_table_length = 500
    if len(table) > max_table_length:
        table = table[:max_table_length:]

    if table:
        for i in range(len(table)):
            label1 = Label(frame_local_server.scrollable_frame, text=table[i].strip()[:70:],
                           fg="black",
                           bg="#eee",
                           font="Helvetica 14 bold",
                           width=80,
                           bd=0,
                           borderwidth=0)
            label1.grid(row=i, column=0, columnspan=2, padx=20, pady=10)

            btn = Button(frame_local_server.scrollable_frame, text="Скачать",  # текст кнопки
                         background="black",  # фоновый цвет кнопки
                         foreground="white",  # цвет текста
                         padx="20",  # отступ от границ до содержимого по горизонтали
                         pady="5",  # отступ от границ до содержимого по вертикали
                         font="Helvetica 12 bold",  # высота шрифта
                         command=lambda c=i: copy_result_from_server(c, paths, table)
                         )
            btn.grid(row=i, column=3, padx=20)

    else:
        show_message('По запрашиваемой строке информации на сервере нет', frame_local_server)


def copy_result_from_server(i, paths, table):
    src = paths[i]
    dst = str(pathlib.Path(__file__).parent.absolute()) + f'\\{table[i]}'
    # print(table[i])
    copyfile(src, dst)
    messagebox.showinfo("Успешное копирование", f'Скопирован файл {table[i]}')


def save_result_to_file(data_to_write):
    with open('files_on_server.json', 'w') as f:
        f.write(json.dumps(data_to_write))


def show_message(message_text, current_frame):
    label_err_info = Label(current_frame.scrollable_frame, text=message_text,
                           fg="black",
                           bg="#eee",
                           font="Helvetica 20 bold",
                           width=70,
                           bd=0,
                           borderwidth=0)
    label_err_info.grid(row=0, column=0, padx=20, pady=10)


def server_db_or_folder_search():
    global local_db_search
    if local_db_search:
        local_db_search = False
        toggle_btn['text'] = "Включен поиск в папке сервера"
    else:
        local_db_search = True
        toggle_btn['text'] = "Включен поиск в локальной базе сервера"



#######

root = Tk()

# Window settings
root.title("Web search client")
root.resizable(False, False)
width = 1200
heigth = 890
root.geometry(f"{width}x{heigth}+300+50")
root.configure(background='black')

# Bind Enter to "Искать" button
root.bind('<Return>', represent_results)

# Grid columns setting
root.columnconfigure(0, weight=1)
root.columnconfigure(1, weight=1)
root.columnconfigure(2, weight=1)

# Place company label
img = ImageTk.PhotoImage(Image.open("./img/title_img.png"))
logo = Label(root, image=img)
logo.grid(row=0, column=2)
logo.configure(background='black')


updt_btn = Button(text="Обновить локальную базу данных сервера",  # текст кнопки
                  background="black",  # фоновый цвет кнопки
                  foreground="grey",  # цвет текста
                  padx="25",  # отступ от границ до содержимого по горизонтали
                  pady="5",  # отступ от границ до содержимого по вертикали
                  font="Helvetica 12 bold",  # высота шрифта
                  command=update_db)
updt_btn.grid(row=0, column=0, padx=19, pady=5, sticky=W + N)


toggle_btn = Button(text="Включен поиск в локальной базе сервера",  # текст кнопки
             background="black",  # фоновый цвет кнопки
             foreground="grey",  # цвет текста
             padx="25",  # отступ от границ до содержимого по горизонтали
             pady="5",  # отступ от границ до содержимого по вертикали
             font="Helvetica 12 bold",  # высота шрифта
             command=server_db_or_folder_search)
toggle_btn.grid(row=0, column=1, padx=5, pady=5, sticky=W+N)


message = StringVar()

message_entry = Entry(textvariable=message,
                      width=50,
                      font="Helvetica 28 bold",
                      bg='black',
                      fg='white',
                      bd=1)

message_entry.focus_set()
message_entry.grid(row=1, column=0, columnspan=2, padx=20, pady=20)

# Button 'Search'
updt_btn = Button(text="Искать",  # текст кнопки
                  background="black",  # фоновый цвет кнопки
                  foreground="white",  # цвет текста
                  padx="25",  # отступ от границ до содержимого по горизонтали
                  pady="5",  # отступ от границ до содержимого по вертикали
                  font="Helvetica 16 bold",  # высота шрифта
                  command=represent_results)
updt_btn.grid(row=1, column=2, padx=20)

# Create custom style
style = ttk.Style()
style.theme_create("MyStyle",
                   parent="classic",
                   settings={
                       "TNotebook.Tab": {
                           "configure": {"padding": [15, 15],
                                         "background": "black",
                                         "foreground": "white",
                                         "font": "-family {DejaVu Sans} -size 20 -weight bold"
                                                 " -slant roman -underline 0 -overstrike 0"
                                         },
                           "map": {"background": [("selected", "white")],
                                   "foreground": [("selected", "black")],
                                   "expand": [("selected", [5, 5, 5, 0])]}
                       }
                   }
                   )

style.theme_use("MyStyle")

# Create 2 tabs
tabControl = ttk.Notebook(root)
tab1 = Frame(tabControl)
tabControl.add(tab1, text='     Результаты поиска в "WebSearch"    ')

tab2 = Frame(tabControl)
tabControl.add(tab2, text='   Результаты поиска на сервере "Tech"  ')

tabControl.grid(row=2, column=0, columnspan=3, padx=20, pady=10, sticky=N + S + E + W)


def _on_mousewheel(event):
    frame_web_search.canvas.yview_scroll(-1 * (event.delta // 120), "units")
    frame_local_server.canvas.yview_scroll(-1 * (event.delta // 120), "units")


# Frame for WebSearch results
frame_web_search = ScrollableFrame(tab1)
frame_web_search.configure(background='black')
frame_web_search.bind_all("<MouseWheel>", _on_mousewheel)
frame_web_search.grid(row=0, column=0, columnspan=3)

# Frame for Server results
frame_local_server = ScrollableFrame(tab2)
frame_local_server.configure(background='black')
frame_local_server.bind_all("<MouseWheel>", _on_mousewheel)
frame_local_server.grid(row=0, column=0, columnspan=3)

# frame_web_search.scrollbar.pack_forget()

# Инициализация сессии и авторизация
try:
    my_session = start_session()
    log_in(login, password, my_session)
except:
    show_message('Ошибка соединения с "WebSearch"', frame_web_search)
    web_connection_flag = False


root.mainloop()
