'''
Notes:  this script is to be run on the WPress Server itself. 
        loops through PDF files in /wp-content/uploads:

        - create YYYY/MM directory
        - move PDF to YYYY/MM directory
        - pdfToText the PDF 
        - INSERT PDF Text, PDF file informaiton (incl SHA) to WP database
Requires:
        - apt install cron  ( if you want to schedule the script)
        - apt install vim  ( edit the crontab -e)

        cat <<EOF | tee process_uploads.sh
            cd /var/www/html/wp-content/python
            python3 process_uploads.py
        EOF
'''

########################################################################

import os as os
from datetime import datetime

PWD = os.getenv('PWD')

def file_write(path, data, mode='w'):
    f = open(path, mode)
    f.write(data)
    f.close()

def file_read(path):
    f = open(path, "r")
    return f.read()

def clean():

    file_write(PWD+f'/'+'.dbenv').remove()
    file_write(PWD+f'/'+'.wpenv').remove()
    file_write(PWD+f'/'+'.dbmaster').remove()

    print('[ reset ] : db,wp,master envs')
    for file in '.dbenv', '.wpenv', '.dbmaster':
        print('[remove ] : ' + file)
        utils.file(PWD+f'/'+file).remove()

########################################################################

def set_master_db():
    formats.msg_dash()
    formats.msg_info('[ config ] : .dbmaster')
    utils.file(PWD+f'/'+'.dbmaster').write('WPMDB01'+f':'+'master'+f':'+'wp_maria_master'+f':'+str(3306), 'w')
    dbMasterEnv = utils.file(PWD+f'/'+'.dbmaster').read().split(':')
    formats.msg_info('dbMasterEnvFile: ' + PWD+f'/'+'.dbmaster')
    formats.msg_info('dbMasterEnv    : ' + str(dbMasterEnv))

def dbenv(instance_name, dbPort):
    # utils.file(PWD+f'/'+'.dbenv').write('WPMDB01'+f':'+'wordpress_'+instance_name+f':'+'wp_maria_master'+f':'+str(dbPort), 'w')
    DATA = str('WPMDB01'+f':'+'wordpress_'+instance_name+f':'+'wp_maria_master'+f':'+str(dbPort))
    file_write(PWD+f'/'+'.dbenv', DATA, 'w')
    return DATA

def wpenv(instance_name, port):
    # utils.file(PWD+f'/'+'.wpenv').write(instance_name+f':'+'wp_server_'+instance_name+f':'+str(port)+f':'+'wordpress_'+instance_name+f':'+'wp_maria_master','w')
    wpContainerName = 'wp_server_'+instance_name
    wpPort = str(port)
    wpDbName = 'wordpress_'+instance_name
    wpDbMaster = 'wp_maria_master'
    DATA = instance_name \
                + f':' \
                + wpContainerName \
                + f':' \
                + wpPort \
                + f':' \
                + wpDbName \
                + f':' \
                + wpDbMaster
                # 
    file_write(PWD+f'/'+'.wpenv', DATA,'w')
    return DATA

########################################################################

class Environment:
    PWD = os.getenv('PWD')
    HOME = os.getenv('HOME')
    WORKDIR = HOME + f'/' + f'.work'
    YYYY_MM = datetime.now().strftime("%Y/%m") 
    YYYY = datetime.now().strftime("%Y") 
    dbEnv = file_read(PWD+f'/'+'.dbenv')
    dbInstanceName = dbEnv.split(':')[0]
    dbName = dbEnv.split(':')[1]
    dbContainerName = dbEnv.split(':')[2]
    dbPort = dbEnv.split(':')[3]
    wpEnv = file_read(PWD+f'/'+'.wpenv')
    wpInstanceName = wpEnv.split(':')[0]
    wpContainerName = wpEnv.split(':')[1]
    wpPort = wpEnv.split(':')[2]
    wpDbName = wpEnv.split(':')[3]
    wpDbMaster = wpEnv.split(':')[4]
    wpUploadsDir = f'/var/www/html/wp-content/uploads'
    wpUploadsDirYYYYMM = wpUploadsDir + f'/' + YYYY_MM

########################################################################

class Uploads(Environment):

    def shell_command(self, command):
        import subprocess
        DATA = subprocess.check_output(command, shell=True)
        res = DATA.decode("utf-8")
        # print(res)
        return res

    def is_directory(self, path):
        CMD = '[' + ' -d ' + path + ' ]' + ' && echo 1 || echo 0'
        res = self.shell_command(CMD)
        if int(res) == 1:
            return True
        else:
            return False

    def is_file(self, path):
        CMD = f"[ -f " + path + f" ] && echo 1 || echo 0"
        res = str(self.shell_command(CMD)).replace('\r',f'').replace('\n',f'')
        if int(res) == 1:
            return True
        else:
            return False

    def create_directory(self, path):
        CMD = 'mkdir -p ' + path
        res = self.shell_command(CMD)
        if self.is_directory(path) is True:
            return True
        else:
            return False

    def copy(self, path, newPath):
        CMD = 'cp '+file+' '+newPath
        res = self.shell_command(CMD)
    
    def shasum(self, path, length=None):

        if length is None:
            CMD = 'shasum '+path
        else:
            CMD = 'sha'+str(length)+'sum' + f' ' + path
        res = self.shell_command(CMD).split()
        return res
    
    def basename(self, path):
        
        RES = str(path.split(f'/')[-1:])
        RES = RES.replace(f"['",'').replace(f"']",'')
        return RES

    def dirname(self, path):
        directory = []
        for i in path.split(f'/')[1:-1]:
            directory.append(i)
        return directory

    def sql(self, sql, dmlFile=None, mode=None):

        if mode == f'r':
            CMD = 'mariadb --skip-column-names -h mysql -u root -ppassword01 ' \
            + self.wpDbName \
            + f' < "' \
            + dmlFile \
            + f'"' 
        elif mode == f'w':       
            file_write(dmlFile, sql+'\n', mode)
            CMD = 'echo '
        elif mode is None and dmlFile is None:
            CMD = 'mariadb --skip-column-names -h mysql -u root -ppassword01 ' \
                + self.wpDbName \
                + f' -e "' \
                + sql \
                + f'"'
        else:
            CMD = 'echo '
        return self.shell_command(CMD)

    def show_tables(self):
        SQL = f'show tables;'
        return self.sql(SQL)

    def describe(self,table_name):
        SQL = f'show columns from ' + table_name + f';'
        return self.sql(SQL)

    def is_row(self,table_name, column, value):
        SQL = """select distinct count(*) as cnt """ \
              + """ FROM """ \
              + table_name \
              + f""" WHERE """ \
              + column \
              + " = '" \
              + value + "';"
        print(SQL)
        res = self.sql(SQL).strip()
        print('[res] ' + str(res))

        if res == f'':
            res = 0
        elif res is None:
            res = 0

        if int(res) == 1:
            return True
        else:
            return False

    def create_table(self, drop=None):

        dmlFile=PWD+f'/'+'create_table.sql'
        
        if drop is not None:

            SQL = """DROP TABLE IF EXISTS wp_auto_upload_file;\n"""
            file_write(dmlFile, SQL,'w')
            # self.sql(SQL, dmlFile, mode='w')

        SQL = """CREATE TABLE IF NOT EXISTS wp_auto_upload_file (
                     file_id bigint(20) unsigned NOT NULL AUTO_INCREMENT
                  ,  file_name text DEFAULT NULL
                  ,  file_path text DEFAULT NULL
                  ,  file_size int(11) DEFAULT NULL
                  ,  file_cacl text DEFAULT NULL
                  ,  file_owner text DEFAULT NULL
                  ,  file_group text DEFAULT NULL
                  ,  file_shasum text DEFAULT NULL
                  ,  file_sha256sum text DEFAULT NULL
                  ,  file_sha512sum text DEFAULT NULL
                  ,  file_info text DEFAULT NULL
                  ,  wp_wfu_idlog int(11) DEFAULT NULL
                  ,  file_text LONGTEXT DEFAULT NULL
                  ,  file_title  text DEFAULT NULL
                  ,  upload_date datetime DEFAULT CURRENT_TIMESTAMP
                  ,  source_url text DEFAULT NULL
                  ,  uploaded_by text DEFAULT NULL
                  ,  PRIMARY KEY (file_id)
                  ) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci; """

                    # ALTER TABLE wp_auto_upload_file RENAME COLUMN title TO file_title;


        file_write(dmlFile, SQL,'a')
        SQL = f'ALTER TABLE wp_auto_upload_file ADD CONSTRAINT UNIQUE_wp_auto_upload_file_SHASUM UNIQUE (file_shasum);'
        file_write(dmlFile, SQL,'a')
        self.sql(SQL, dmlFile, mode='r')

    def create_view(self):
        
        dmlFile = PWD+f'/'+'create_view.sql'
        SQL = """
            DROP VIEW IF EXISTS V_WP_AUTO_UPLOAD_FILE;
            """
        file_write(dmlFile, SQL,'w')
        # self.sql(SQL, dmlFile=dmlFile, mode='w')

        SQL = """
            CREATE VIEW V_WP_AUTO_UPLOAD_FILE
            AS
            SELECT file_id       
                , file_name
                , REPLACE(
                    REPLACE(file_name,'.pdf','')
                    , '_'
                    , ' '
                    ) as file_title
                , CONCAT(ROUND(file_size / 1024), ' kb') as size    
                -- , file_cacl     
                -- , file_owner    
                -- , file_group    
                , file_shasum   
                -- , file_sha256sum
                -- , file_sha512sum
                -- , file_info     
                , wp_wfu_idlog
                , SUBSTR(REPLACE(
                           REPLACE(
                                   REPLACE(
                                           file_text, '__SGL_QTE__', "'"
                                   ), '__DBL_QTE__', '"'
                           ), '__CHEVR__', '^'
                 ),1,50) as file_text
               , CONCAT('http://192.168.1.133/wp-admin/wp-content/uploads/2023/11/',REPLACE(file_name,'.pdf','.txt'),'||FULL TEXT') as link
               -- https://wpdatatables.com||Check out wpDataTables
             FROM wp_auto_upload_file
             ;
             """
        file_write(dmlFile, SQL,'a')
        self.sql(SQL, dmlFile=dmlFile, mode='r')

    def file_info(self, path):
        CMD = 'ls -al ' + path
        return self.shell_command(CMD)

    def file_names(self):

        uploads = os.listdir(self.wpUploadsDir)
        for path in uploads:
            if f'.pdf' in path:
                # print(path)
                newFileName = path.replace("'",'-').replace(' ','_')
                if newFileName != path:
                   
                    CMD = 'mv ' \
                        + self.wpUploadsDir \
                        + f'/' \
                        + path.replace(' ', '\ ').replace("'","\'") \
                        + ' ' \
                        + self.wpUploadsDir \
                        + f'/' \
                        + newFileName

                    self.shell_command(CMD)
                    print(CMD)


class Convert(Environment):

    def pdfToText(self, path, destDir=None):
        pathName = Uploads().basename(path)
        pathExt = Uploads().basename(pathName)

        CMD = f'/usr/bin/pdftotext -layout' \
            + f' ' \
            + path 
        if destDir is not None:
            destFile = destDir + f'/' + pathName.replace('.pdf','.txt')
            CMD = CMD + f' ' + destFile
        else:
            destFile = path.replace('.pdf','.txt')

        Uploads().shell_command(CMD)
        return destFile

class Process(Environment):

    def configure(self):
        #--- check: directory() ---#    
        if Uploads().is_directory(self.wpUploadsDirYYYYMM) is not True:

            print(f'[' \
                + str(Uploads().create_directory(self.wpUploadsDirYYYYMM)) \
                + f'] create directory : ' \
                + self.wpUploadsDirYYYYMM)
        
        Uploads().create_table(drop=True)
        Uploads().create_view()

    def inject(self, table_name, dataSet):

        dmlFile=PWD+f'/'+'process_inject.sql'
        dataSet = dataSet.split('^')

        print('[insert] Uploads().is_row(table_name, column, shaValue) is False')

        ####################################
        SQL = """\nINSERT INTO """ + table_name + """
                ( file_name
                    , file_path
                    , file_shasum
                    , file_sha256sum
                    , file_sha512sum
                    , file_cacl
                    , file_owner
                    , file_group
                    , file_size
                    , file_info
                    )
                VALUES
                    ('""" + dataSet[0] \
                        + f"', '" + dataSet[1] \
                        + f"', '" + dataSet[2] \
                        + f"', '" + dataSet[3] \
                        + f"', '" + dataSet[4] \
                        + f"', '" + dataSet[5] \
                        + f"', '" + dataSet[6] \
                        + f"', '" + dataSet[7] \
                        + f"', '" + dataSet[8] \
                        + f"', '" + str(dataSet[9]).replace("'",'"') \
                        + """');"""

        ####################################
        file_write(dmlFile, SQL, 'w')
        Uploads().sql(SQL, dmlFile, mode='r')
        ####################################

    def update(self, table_name, dataSet):

        dmlFile=PWD+f'/'+'process_update.sql'

        print('[update] Uploads().is_row(table_name, column, shaValue) is True' )

        SQL = f"""\nUPDATE """   + table_name + """
                    SET file_name = '"""     + dataSet[0] + """'
                        , file_path = '"""       + dataSet[1] + """'
                        , file_sha256sum = '"""  + dataSet[2] + """'
                        , file_sha512sum = '"""  + dataSet[3] + """'
                        , file_cacl = '"""       + dataSet[4] + """'
                        , file_owner = '"""      + dataSet[5] + """'
                        , file_group = '"""      + dataSet[6] + """'
                    WHERE file_shasum = '""" + dataSet[7] + """';"""


        #####################################
        file_write(dmlFile, SQL, 'w')
        Uploads().sql(SQL, dmlFile, mode='r')
        #####################################

    def convert(self, source_path, table_name, shaValue):

        dmlFile=PWD+f'/'+'extract_text.sql'
        pdfToTextFile = Convert().pdfToText(source_path, destDir=self.wpUploadsDirYYYYMM)
        
        f = open(pdfToTextFile, "r")
        pdfToText = str(f.read())

        pdfText = pdfToText.replace("'","__SGL_QTE__")
        pdfText = pdfText.replace('"',"__DBL_QTE__")
        pdfText = pdfText.replace('^',"__CHEVR__")

        print('[update] ' + table_name + f'.' + f'file_text()')

        #####################################
        SQL = f"""\nUPDATE """ + table_name + """
                     SET file_text = '""" + pdfText + """' 
                         WHERE file_shasum = '""" + shaValue + """';"""
        file_write(dmlFile, SQL, 'a')
        Uploads().sql(SQL, dmlFile, mode='r')
        #####################################

    def uploads(self):

        files = Uploads().shell_command('ls -1 ' + self.wpUploadsDir + f'/*.pdf').split()
        print('[process_candidates] ' + str(files))
        Uploads().file_names()
        
        for file in files:
            
            if file is not None:

                fileName = Uploads().basename(file)
                newFileName = fileName.replace('.pdf','')
                newFileName = newFileName.replace("'",'-').replace(' ','_').replace('"','-').replace('.','-')
                newFilePath = self.wpUploadsDirYYYYMM + f'/'+ newFileName + f'.pdf'

                if Uploads().is_file(newFilePath) is not True:
                    CMD = 'mv '+file+' '+newFilePath
                    res = Uploads().shell_command(CMD)
               
                shaValue = Uploads().shasum(newFilePath)[0]
                sha256Value = Uploads().shasum(newFilePath, 256)[0]
                sha512Value = Uploads().shasum(newFilePath, 512)[0]
                fileInfo = Uploads().file_info(newFilePath).split()
                fileCacl = fileInfo[0]
                fileOwner = fileInfo[2]
                fileGroup = fileInfo[3]
                fileSize = fileInfo[4]

                table_name = f'wp_auto_upload_file'
                column = f'file_shasum'

                if Uploads().is_row(table_name, column, shaValue) is False:

                    dataSet = fileName \
                            + f"^" + newFilePath \
                            + f"^" + shaValue \
                            + f"^" + sha256Value \
                            + f"^" + sha512Value \
                            + f"^" + fileCacl \
                            + f"^" + fileOwner \
                            + f"^" + fileGroup \
                            + f"^" + fileSize \
                            + f"^" + str(fileInfo).replace("'",'"')

                    self.inject(table_name, dataSet)

                else:

                    dataSet = newFilePath \
                        + f"^" + newFilePath \
                        + f"^" + sha256Value \
                        + f"^" + sha512Value \
                        + f"^" + fileCacl \
                        + f"^" + fileOwner \
                        + f"^" + fileGroup \
                        + f"^" + shaValue
                    
                    self.update(table_name, dataSet)

                if Uploads().is_row(table_name, f'file_name', newFilePath) is True:

                    if Uploads().is_file(newFilePath) is True:

                        #####################################
                        CMD = 'rm -f ' + file
                        Uploads().shell_command(CMD)
                        #####################################
                        print('[update] Uploads().is_row(table_name, column, shaValue) is True')

                self.convert(newFilePath, 'wp_auto_upload_file', shaValue)

        else:
                print('[message] nothing to process... all good!!')
  
def main():

    dbenv('tdlo',3306)
    wpenv('tdlo', 8081)
    Process().configure()
    Process().uploads()


main()    
