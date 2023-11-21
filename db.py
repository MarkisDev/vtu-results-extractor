import sqlite3
import os
from datetime import date


class Database:
    def __init__(self, path):
        # Initializing important vars
        self.path = path
        self.conn = sqlite3.connect(os.path.join(self.path, 'sem-results.db'))
        self.curr = self.conn.cursor()
        try:
            # Creating tables for reval and reg because they have different formats
            self.curr.execute('''
                CREATE TABLE IF NOT EXISTS reg(
                    usn varchar(20) NOT NULL,
                    name varchar(200) NOT NULL,
                    sem int NOT NULL, 
                    sub_code varchar(200) NOT NULL,
                    sub_name text NOT NULL,
                    internal int NOT NULL,
                    external int NOT NULL,
                    total int NOT NULL,
                    result varchar(3) NOT NULL,
                    announced date,
                    date date,
                    PRIMARY KEY(usn,name,sub_code,sub_name,internal,external,total,result,announced,date));
            ''')
            self.curr.execute('''
                CREATE TABLE IF NOT EXISTS rev(
                    usn varchar(20) NOT NULL,
                    name varchar(200) NOT NULL,
                    sem int NOT NULL, 
                    sub_code varchar(200) NOT NULL, 
                    sub_name text NOT NULL,
                    internal int NOT NULL,
                    old_m int NOT NULL,
                    old_res varchar(3) NOT NULL,
                    rv_m int NOT NULL,
                    rv_res varchar(3) NOT NULL,
                    final_m int NOT NULL,
                    final_res varchar(3) NOT NULL,
                    date date NOT NULL,
                    PRIMARY KEY(usn,name,sem,sub_code,sub_name,internal,old_m,old_res,rv_m,rv_res,final_m,final_res,date));
''')
            self.conn.commit()
        except:
            raise Exception("An error occured with DB initialization!")

    def insertRecord(self, reval, usn, name, sem, *args):
        try:
            # Making data tuple with *args to make a common insert function
            data = (usn, name, sem, *args, date.today())
            if not reval:
                self.curr.execute('''
                INSERT OR IGNORE INTO reg(
                    usn,
                    name, 
                    sem, 
                    sub_code, 
                    sub_name, 
                    internal, 
                    external, 
                    total, 
                    result, 
                    announced, 
                    date) 
                    values(?,?,?,?,?,?,?,?,?,?,?);
                ''', data)
            else:
                self.curr.execute('''
                INSERT OR IGNORE INTO rev(
                    usn,
                    name,
                    sem, 
                    sub_code,
                    sub_name,
                    internal,
                    old_m,
                    old_res,
                    rv_m,
                    rv_res,
                    final_m,
                    final_res,
                    date
                ) values(?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', data)
            self.conn.commit()
        except Exception as e:
            raise Exception(f"Error occured with inserting record!")

    def getData(self, usn, reval, sem):
        try:
            if not reval:
                statement = f'SELECT * from reg WHERE usn="{usn}" AND sem={sem}'
            else:
                statement = f'SELECT * from rev WHERE usn="{usn}" AND sem={sem}'
            self.curr.execute(statement)
            return self.curr.fetchall()
        except:
            raise Exception("Error occured while selecting data!")

    def doesUsnExist(self, usn, reval):
        try:
            if not reval:
                statement = f'SELECT * from reg WHERE usn="{usn}"'
            else:
                statement = f'SELECT * from rev WHERE usn="{usn}"'

            self.curr.execute(statement)
            data = self.curr.fetchall()

            if len(data) >= 1:
                return True
            else:
                return False
        except Exception as e:
            raise Exception("Error occured while checking USN!")

    def findMaxSem(self, usn, reval):
        try:
            if not reval:
                statement = f'SELECT max(sem) from reg WHERE usn="{usn}"'
            else:
                statement = f'SELECT max(sem) from rev WHERE usn="{usn}"'

            self.curr.execute(statement)
            return self.curr.fetchall()
        except:
            raise Exception('Error occured fetching max sem')

    def getAllUsn(self):
        try:
            regStatement = f'SELECT DISTINCT usn from reg'
            revStatement = f'SELECT DISTINCT usn from rev'
            self.curr.execute(regStatement)
            temp = self.curr.fetchall()
            reg = [usn for sublist in temp for usn in sublist]
            self.curr.execute(revStatement)
            temp = self.curr.fetchall()
            reval = [usn for sublist in temp for usn in sublist]
            return reg, reval
        except:
            raise Exception("Error occured while fetching all USN's!")

    def truncate(self):
        try:
            statement = 'DELETE from reg'
            self.curr.execute(statement)
            statement = 'DELETE from rev'
            self.curr.execute(statement)
            self.conn.commit()
            return True
        except:
            raise Exception("Error occured while truncating!")

    def __del__(self):
        try:
            # Destructor will close db
            self.conn.close()
        except:
            raise Exception("Error occured closing DB!")
