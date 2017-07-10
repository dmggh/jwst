try:
    import pymysql
    pymysql.install_as_MySQLdb() 
except Exception as exc:
    print("WARNING: FAILED to import and initialize pymsql")



