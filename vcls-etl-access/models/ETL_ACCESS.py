import pyodbc

class ETL_ACCESS:
    
    __instance = None
    instance = None

    @staticmethod
    def getInstance():
        if ETL_ACCESS.__instance == None:
            ETL_ACCESS()
        return ETL_ACCESS.__instance

    def __init__(self):
        """ Virtually private constructor. """
        if ETL_ACCESS.__instance != None:
            raise Exception("This class is a singleton!")
        else:

            ETL_ACCESS.__instance = self
            conn_str = (
                r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
                r'DBQ=C:\Users\laamouri\OneDrive - VOISIN CONSULTING\Desktop\B&H Database\database backup\BHTbls.accdb;'
            )
            cnxn = pyodbc.connect(conn_str)
            ETL_ACCESS.instance = cnxn.cursor()

    def getConnection(self):
        return ETL_ACCESS.instance