import peewee
import os
import config

db_file_name = 'server_files.db'

server_address = config.server_address
database = peewee.SqliteDatabase(db_file_name)


class Files(peewee.Model):
    path = peewee.CharField()
    name = peewee.CharField()

    class Meta:
        database = database


database.create_tables([Files])


def find_files():
    data = []
    for roots, dirs, files in os.walk(f"{server_address}"):
        for file in files:
            data.append((os.path.join(roots, file), file))
    print('done')
    return data


def commit_data_to_db():
    data = find_files()
    batch_size = 100

    for point in range(0, len(data), batch_size):
        query = Files.insert_many(data[point:(point + batch_size):1], fields=[Files.path, Files.name])
        query.execute()


def find_path_in_db(name: str) -> list:
    paths = []
    files = Files.select().where(Files.name.contains(name.lower())
                                 | (Files.name.contains(name.upper()))
                                 | Files.name.contains(name.lower().capitalize()))

    for file in files:
        paths.append(file.path)
    return paths


def find_name_in_db(name: str) -> list:
    names = []
    files = Files.select().where(Files.name.contains(name.lower())
                                 | (Files.name.contains(name.upper()))
                                 | Files.name.contains(name.lower().capitalize()))

    for file in files:
        names.append(file.name)
        # print(file.name)
    return names


def update_db():
    global database
    database.close()

    path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'server_files.db')
    os.remove(path)

    database = peewee.SqliteDatabase('server_files.db')
    database.create_tables([Files])

    find_files()
    commit_data_to_db()
