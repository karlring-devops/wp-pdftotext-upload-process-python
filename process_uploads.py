'''
Notes:  this script is to be run on the WPress Server itself. 
        loops through PDF files in /wp-content/uploads:

        - create YYYY/MM directory
        - move PDF to YYYY/MM directory
        - pdfToText the PDF 
        - INSERT PDF Text, PDF file informaiton (incl SHA) to WP database
'''


import os as os
from datetime import datetime

class Environment:
    HOME = os.getenv('HOME')
    WORKDIR = HOME + f'/' + f'.work'
    DIR_UPLOADS = f'/var/www/html/wp-content/uploads'
    wpUploadsDir = f'/var/www/html/wp-content/uploads'
    YYYY_MM = datetime.now().strftime("%Y/%m") 
    YYYY = datetime.now().strftime("%Y") 
    wpUploadsDirYYYYMM = wpUploadsDir + f'/' + YYYY_MM
    wpDbName = 'wordpress_trp'

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

    def sql(self, sql):
        CMD = 'mariadb --skip-column-names -h mysql -u root -ppassword01 ' \
            + self.wpDbName \
            + f' -e "' \
            + sql \
            + f'"'
        return self.shell_command(CMD)

    def show_tables(self):
        SQL = f'show tables;'
        return self.sql(SQL)

    def describe(self,table_name):
        SQL = f'show columns from ' + table_name + f';'
        return self.sql(SQL)

    def is_row(self,table_name, column, value):
        SQL = """select distinct 1 """ \
              + """ FROM """ \
              + table_name \
              + f""" WHERE """ \
              + column \
              + " = '" \
              + value + "';"

        # print(SQL)
        res = self.sql(SQL).strip()

        if res == f'':
            res = 0
        elif res is None:
            res = 0

        if int(res) == 1:
            return True
        else:
            return False

    def file_info(self, path):
        CMD = 'ls -al ' + path
        return self.shell_command(CMD)

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
            print(f'[' + str(Uploads().create_directory(self.wpUploadsDirYYYYMM)) + f'] create directory : ' + self.wpUploadsDirYYYYMM)

    def uploads(self):

        try:
            files = Uploads().shell_command('ls -1 ' + self.wpUploadsDir + f'/*.pdf').split()
            #--- check: file(new) ---#    
            for file in files:
                
                if file is not None:
                    fileName = Uploads().basename(file)
                    newFileName = self.wpUploadsDirYYYYMM + f'/'+ fileName

                    if Uploads().is_file(newFileName) is not True:
                        CMD = 'cp '+file+' '+newFileName
                        res = Uploads().shell_command(CMD)
                   
                    shaValue = Uploads().shasum(newFileName)[0]
                    sha256Value = Uploads().shasum(newFileName, 256)[0]
                    sha512Value = Uploads().shasum(newFileName, 512)[0]
                    fileInfo = Uploads().file_info(newFileName).split()
                    fileCacl = fileInfo[0]
                    fileOwner = fileInfo[2]
                    fileGroup = fileInfo[3]
                    fileSize = fileInfo[4]

                    print('[newFileName] ' + newFileName)
                    print('[shaValue   ] ' + shaValue)
                    print('[sha256Value] ' + sha256Value)
                    print('[file cacls ] ' + fileCacl)
                    print('[file owner ] ' + fileOwner)
                    print('[file group ] ' + fileGroup)

                    SQL = f"select file_name, file_shasum from wp_auto_upload_file where file_shasum = '"+shaValue+"';"
                    print(Uploads().sql(SQL).strip())

                    table_name = f'wp_auto_upload_file'
                    column = f'file_shasum'
                    print(table_name+':'+column+':'+shaValue + '\n')

                    if Uploads().is_row(table_name, column, shaValue) is True:

                        SQL = f"""UPDATE """ + table_name + """
                                     SET file_name = '""" + newFileName + """'
                                       , file_sha256sum = '""" + sha256Value + """'
                                       , file_sha512sum = '""" + sha512Value + """'
                                       , file_cacl = '""" + fileCacl + """'
                                       , file_owner = '""" + fileOwner + """'
                                       , file_group = '""" + fileGroup + """'
                                         WHERE file_shasum = '""" + shaValue + """';"""
                        res = Uploads().sql(SQL)

                        if Uploads().is_row(table_name, f'file_name', newFileName) is True:
                            if Uploads().is_file(newFileName) is True:
                                CMD = 'rm -f ' + file
                                Uploads().shell_command(CMD)
                        print('[update] yeah baby!!')
                    else:
                        SQL = """INSERT INTO """ + table_name + """
                                ( file_name
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
                                    ('""" + newFileName \
                                        + f"', '" + shaValue \
                                        + f"', '" + sha256Value \
                                        + f"', '" + sha512Value \
                                        + f"', '" + fileCacl \
                                        + f"', '" + fileOwner \
                                        + f"', '" + fileGroup \
                                        + f"', '" + fileSize \
                                        + f"', '" + str(fileInfo).replace("'",'"') \
                                        + """');"""
                        print(SQL)
                        res = Uploads().sql(SQL)
                        print('[insert] feels goooood !!')

                    pdfToTextFile = Convert().pdfToText(newFileName, destDir=self.wpUploadsDirYYYYMM)
                    
                    f = open(pdfToTextFile, "r")
                    pdfToText = str(f.read())

                    pdfText = pdfToText.replace("'","__SGL_QTE__")
                    pdfText = pdfText.replace('"',"__DBL_QTE__")
                    pdfText = pdfText.replace('^',"__CHEVR__")
                    # f.read()

                    SQL = f"""UPDATE """ + table_name + """
                                 SET file_text = '""" + pdfText + """' 
                                     WHERE file_shasum = '""" + shaValue + """';"""
                    print(SQL)
                    res = Uploads().sql(SQL)
        except Exception as e:
            print('[message] nothing to process... all good!!')
  
def main():

    Process().configure()
    Process().uploads()


main()