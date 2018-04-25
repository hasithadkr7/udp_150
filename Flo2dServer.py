from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse as url_parser
import fnmatch
import os
import zipfile
import json
from google.cloud import storage


def get_config():
    with open('CONFIG.json') as json_file:
        return json.load(json_file)
    
    
# Refer: http://stackoverflow.com/a/13146494/1461060
class StoreHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        print("http GET....")
        config_data = get_config()
        url, query = url_parser.splitquery(self.path)
        if query.split('&')[0].split('=')[0] == 'wrf' and query.split('&')[1].split('=')[0] == 'hec':
            wrf_id = query.split('&')[0].split('=')[1]
            hec_id = query.split('&')[1].split('=')[1]
            print("wrf_id:", wrf_id)
            print("hec_id:", hec_id)
            try:
                print("get_wrf_files...")
                client = storage.Client.from_service_account_json(config_data["KEY_FILE_PATH"])
                bucket = client.get_bucket(config_data["BUCKET_NAME"])
                prefix = config_data["INITIAL_PATH_PREFIX"] + wrf_id + '_'
                blobs = bucket.list_blobs(prefix=prefix)
                for blob in blobs:
                    if fnmatch.fnmatch(blob.name, "*" + config_data["WRF_RAINCELL_FILE_ZIP"]):
                        directory = config_data["WINDOWS_PATH"] + wrf_id.split("_")[1]
                        if not os.path.exists(directory):
                            os.makedirs(directory)
                        download_location = directory + '/' + config_data["WRF_RAINCELL_FILE_ZIP"]
                        blob.download_to_filename(download_location)
                        zip_ref = zipfile.ZipFile(download_location, 'r')
                        zip_ref.extractall(directory)
                        zip_ref.close()
                        os.remove(download_location)
                        src_file = directory + '/' + config_data["WRF_RAIN_CELL_FILE"]
                        des_file = directory + '/' + config_data["RAIN_CELL_FILE"]
                        os.rename(src_file, des_file)
                    else:
                        print("File prefix didn't match.")
                hec_prefix = config_data["INITIAL_PATH_PREFIX"] + hec_id + '_'
                hec_blobs = bucket.list_blobs(prefix=hec_prefix)
                for blob in hec_blobs:
                    if fnmatch.fnmatch(blob.name, "*" + "INFLOW.DAT"):
                        directory = config_data["WINDOWS_PATH"] + hec_id.split("_")[1]
                        if not os.path.exists(directory):
                            os.makedirs(directory)
                        download_location = directory + '/"INFLOW.DAT'
                        blob.download_to_filename(download_location)
                    elif fnmatch.fnmatch(blob.name, "*" + "OUTFLOW.DAT"):
                        directory = config_data["WINDOWS_PATH"] + hec_id.split("_")[1]
                        if not os.path.exists(directory):
                            os.makedirs(directory)
                        download_location = directory + '/OUTFLOW.DAT'
                        blob.download_to_filename(download_location)
                    else:
                        print("File prefix didn't match.")
            except Exception as e:
                print('Rain cell/Mean-Ref/Rain fall file download failed|Exception:', e.args)

        else:
            print("Need wrf id and hec id to proceed...")

    def do_POST(self):
        print("http POST....")
        self._set_headers()
        self.wfile.write("<html><body><h1>POST!!!</h1></body></html>")


server = HTTPServer(('localhost', 8080), StoreHandler)
print('Starting httpd server...')
server.serve_forever()


