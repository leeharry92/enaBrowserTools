#
# utils.py
#

import base64
import re
import os
import ssl
import subprocess
import urllib.request as urlrequest
import xml.etree.ElementTree as ElementTree

from http.client import HTTPSConnection

ANON_AUTH = b'anon:anon'

SUPPRESSED = 'suppressed'
PUBLIC = 'public'

XML_FORMAT = 'xml'
EMBL_FORMAT = 'embl'
FASTA_FORMAT = 'fasta'
MASTER_FORMAT = 'master'
SUBMITTED_FORMAT = 'submitted'
FASTQ_FORMAT = 'fastq'
SRA_FORMAT = 'sra'

XML_EXT = '.xml'
EMBL_EXT = '.dat'
FASTA_EXT = '.fasta'
WGS_EMBL_EXT = '.dat.gz'
WGS_FASTA_EXT = '.fasta.gz'
WGS_MASTER_EXT = '.master.dat'

SEQUENCE = 'sequence'
CODING = 'coding'
WGS = 'wgs'
RUN = 'run'
EXPERIMENT = 'experiment'
ANALYSIS = 'analysis'
ASSEMBLY = 'assembly'
STUDY = 'study'
READ = 'read'
SAMPLE = 'sample'

VIEW_URL_BASE = 'http://www.ebi.ac.uk/ena/data/view/'
XML_DISPLAY = '&display=xml'
EMBL_DISPLAY = '&display=text'
FASTA_DISPLAY = '&display=fasta'

READ_RESULT_ID='read_run'
ANALYSIS_RESULT_ID='analysis'
WGS_RESULT_ID='wgs_set'
ASSEMBLY_RESULT_ID='assembly'
SEQUENCE_UPDATE_ID='sequence_update'
SEQUENCE_RELEASE_ID='sequence_release'

WGS_FTP_BASE = 'ftp://ftp.ebi.ac.uk/pub/databases/ena/wgs'

PORTAL_SEARCH_BASE = 'http://www.ebi.ac.uk/ena/portal/api/search?'
RUN_RESULT = 'result=read_run'
ANALYSIS_RESULT = 'result=analysis'
WGS_RESULT = 'result=wgs_set'
ASSEMBLY_RESULT = 'result=assembly'
SEQUENCE_UPDATE_RESULT = 'result=sequence_update'
SEQUENCE_RELEASE_RESULT = 'result=sequence_release'

FASTQ_FIELD = 'fastq_ftp'
SUBMITTED_FIELD = 'submitted_ftp'
SRA_FIELD = 'sra_ftp'
INDEX_FIELD = 'cram_index_ftp'
FASTQ_MD5_FIELD = 'fastq_md5'
SUBMITTED_MD5_FIELD = 'submitted_md5'
SRA_MD5_FIELD = 'sra_md5'
INDEX_MD5_FIELD = None

sequence_pattern_1 = re.compile('^[A-Z]{1}[0-9]{5}(\.[0-9]+)?$')
sequence_pattern_2 = re.compile('^[A-Z]{2}[0-9]{6}(\.[0-9]+)?$')
sequence_pattern_3 = re.compile('^[A-Z]{4}[0-9]{8,9}(\.[0-9]+)?$')
coding_pattern = re.compile('^[A-Z]{3}[0-9]{5}(\.[0-9]+)?$')
wgs_prefix_pattern = re.compile('^[A-Z]{4}[0-9]{2}$')
run_pattern = re.compile('^[EDS]RR[0-9]{6,7}$')
experiment_pattern = re.compile('^[EDS]RX[0-9]{6,7}$')
analysis_pattern = re.compile('^[EDS]RZ[0-9]{6,7}$')
assembly_pattern = re.compile('^GCA_[0-9]{9}(\.[0-9]+)?$')
study_pattern_1 = re.compile('^[EDS]RP[0-9]{6,7}$')
study_pattern_2 = re.compile('^PRJ[EDN][AB][0-9]+$')
sample_pattern_1 = re.compile('^SAM[ND][0-9]{7}$')
sample_pattern_2 = re.compile('^SAMEA[0-9]{6,}$')
sample_pattern_3 = re.compile('^[EDS]RS[0-9]{6,7}$')

def is_sequence(accession):
    return sequence_pattern_1.match(accession) or sequence_pattern_2.match(accession) \
        or sequence_pattern_3.match(accession)

def is_coding(accession):
    return coding_pattern.match(accession)

def is_wgs_set(accession):
    return wgs_prefix_pattern.match(accession)

def is_run(accession):
    return run_pattern.match(accession)

def is_experiment(accession):
    return experiment_pattern.match(accession)

def is_analysis(accession):
    return analysis_pattern.match(accession)

def is_assembly(accession):
    return assembly_pattern.match(accession)

def is_study(accession):
    return study_pattern_1.match(accession) or study_pattern_2.match(accession)

def is_sample(accession):
    return sample_pattern_1.match(accession) or sample_pattern_2.match(accession) \
        or sample_pattern_3.match(accession)

def is_primary_study(accession):
    return study_pattern_2.match(accession)

def is_secondary_study(accession):
    return study_pattern_1.match(accession)

def is_primary_sample(accession):
    return sample_pattern_1.match(accession) or sample_pattern_2.match(accession)

def is_secondary_sample(accession):
    return sample_pattern_3.match(accession)

def get_accession_type(accession):
    if is_study(accession):
        return STUDY
    elif is_run(accession):
        return RUN
    elif is_experiment(accession):
        return EXPERIMENT
    elif is_analysis(accession):
        return ANALYSIS
    elif is_assembly(accession):
        return ASSEMBLY
    elif is_wgs_set(accession):
        return WGS
    elif is_coding(accession):
        return CODING
    elif is_sequence(accession):
        return SEQUENCE
    return None

def accession_format_allowed(accession, format):
    if is_analysis(accession):
        return format == SUBMITTED_FORMAT
    if is_run(accession) or is_experiment(accession):
        return format in [SUBMITTED_FORMAT, FASTQ_FORMAT, SRA_FIELD]
    return format in [EMBL_FORMAT, FASTA_FORMAT]

def group_format_allowed(group, format):
    if group == ANALYSIS:
        return format == SUBMITTED_FORMAT
    if group == READ:
        return format in [SUBMITTED_FORMAT, FASTQ_FORMAT, SRA_FIELD]
    return format in [EMBL_FORMAT, FASTA_FORMAT]

# assumption is that accession and format have already been vetted before this method is called
def get_record_url(accession, format):
    if format == XML_FORMAT:
        return VIEW_URL_BASE + accession + XML_DISPLAY
    elif format == EMBL_FORMAT:
        return VIEW_URL_BASE + accession + EMBL_DISPLAY
    elif format == FASTA_FORMAT:
        return VIEW_URL_BASE + accession + FASTA_DISPLAY
    return None

def is_available(accession):
    url = get_record_url(accession, XML_FORMAT)
    response = urlrequest.urlopen(url)
    record = ElementTree.parse(response).getroot()
    return not 'entry is not found' in record.text

def get_filename(base_name, format):
    if format == XML_FORMAT:
        return base_name + XML_EXT
    elif format == EMBL_FORMAT:
        return base_name + EMBL_EXT
    elif format == FASTA_FORMAT:
        return base_name + FASTA_EXT
    return None

def get_destination_file(dest_dir, accession, format):
    filename = get_filename(accession, format)
    if filename is not None:
        return os.path.join(dest_dir, filename)
    return None

def download_single_record(url, dest_file):
    urlrequest.urlretrieve(url, dest_file)

def download_record(dest_dir, accession, format):
    try:
        dest_file = get_destination_file(dest_dir, accession, format)
        url = get_record_url(accession, format)
        download_single_record(url, dest_file)
        return True
    except Exception:
        return False

def append_record(url, dest_file):
    try:
        response = urlrequest.urlopen(url)
        f = open(dest_file, 'ab')
        for line in response:
            chars = f.write(line)
        f.flush()
        f.close()
        return True
    except Exception:
        return False

def get_ftp_file(ftp_url, dest_dir):
    try:
        filename = ftp_url.split('/')[-1]
        dest_file = os.path.join(dest_dir, filename)
        urlrequest.urlretrieve(ftp_url, dest_file)
        return True
    except Exception:
        return False

def get_md5(filepath):
    p = subprocess.Popen(['md5', filepath], stdout=subprocess.PIPE)
    output, error = p.communicate()
    return output.decode().split('=')[-1].strip()

def get_ftp_file_with_md5_check(ftp_url, dest_dir, md5):
    try:
        filename = ftp_url.split('/')[-1]
        dest_file = os.path.join(dest_dir, filename)
        urlrequest.urlretrieve(ftp_url, dest_file)
        generated_md5 = get_md5(dest_file)
        if md5 != generated_md5:
            print ('MD5 mismatch for downloaded file ' + filepath + '. Deleting file')
            print ('generated md5', generated_md5)
            print ('expected md5', md5)
            os.remove(dest_file)
            return False
        return True
    except Exception:
        return False

def get_wgs_ftp_url(wgs_set, status, format):
    base_url = WGS_FTP_BASE + '/' + status + '/' + wgs_set[:2].lower() + '/' + wgs_set
    if format == EMBL_FORMAT:
        return base_url + WGS_EMBL_EXT
    elif format == FASTA_FORMAT:
        return base_url + WGS_FASTA_EXT
    elif format == MASTER_FORMAT:
        return base_url + WGS_MASTER_EXT

def get_report_from_portal(url):
    userAndPass = base64.b64encode(ANON_AUTH).decode("ascii")
    headers = { 'Authorization' : 'Basic %s' %  userAndPass }
    request = urlrequest.Request(url, headers=headers)
    gcontext = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    return urlrequest.urlopen(request, context=gcontext)

def download_report_from_portal(url, dest_file):
    response = get_report_from_portal(url)
    f = open(dest_file, 'wb')
    for line in response:
        chars = f.write(line)
    f.flush()
    f.close()

def get_accession_query(accession):
    query = 'query="'
    if is_run(accession):
        query += 'run_accession="' + accession + '"'
    elif is_experiment(accession):
        query += 'experiment_accession="' + accession + '"'
    elif is_analysis(accession):
        query += 'analysis_accession="' + accession + '"'
    query += '"'
    return query

def get_file_fields(accession, format, fetch_index):
    fields = 'fields='
    if format == SRA_FORMAT:
        fields += SRA_FIELD + ',' + SRA_MD5_FIELD
    elif format == FASTQ_FORMAT:
        fields += FASTQ_FIELD + ',' + FASTQ_MD5_FIELD
    else:
        fields += SUBMITTED_FIELD + ',' + SUBMITTED_MD5_FIELD
        if fetch_index and not is_analysis(accession):
            fields += ',' + INDEX_FIELD
    return fields

def get_result(accession):
    if is_run(accession) or is_experiment(accession):
        return RUN_RESULT
    else:  # is_analysis(accession)
        return ANALYSIS_RESULT

def get_file_search_query(accession, format, fetch_index):
    return PORTAL_SEARCH_BASE + get_accession_query(accession) + '&' \
        + get_result(accession) + '&' + get_file_fields(accession, format, fetch_index) + '&limit=0'

def parse_file_search_result_line(line, accession, format, fetch_index):
    cols = line.split('\t')
    filelist = cols[1].strip().split(';')
    md5list = cols[2].strip().split(';')
    indexlist = []
    if format == SUBMITTED_FORMAT and fetch_index and not is_analysis(accession):
        indexlist = cols[3].strip().split(';')
    return cols[0].strip(), filelist, md5list, indexlist

def create_dir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def get_group_query(accession):
    query='query='
    if is_primary_study(accession):
        query += 'study_accession="' + accession + '"'
    elif is_secondary_study(accession):
        query += 'secondary_study_accession="' + accession + '"'
    elif is_primary_sample(accession):
        query += 'sample_accession="' + accession + '"'
    elif is_secondary_sample(accession):
        query += 'secondary_sample_accession="' + accession + '"'
    return query

def get_group_fields(group):
    fields = 'fields='
    if group in [SEQUENCE, WGS, ASSEMBLY]:
        fields += 'accession'
    elif group == READ:
        fields += 'run_accession'
    elif group == ANALYSIS:
        fields += 'analysis_accession'
    return fields

def get_group_result(group):
    if group == READ:
        return RUN_RESULT
    elif group == ANALYSIS:
        return ANALYSIS_RESULT
    elif group == WGS:
        return WGS_RESULT
    elif group == ASSEMBLY:
        return ASSEMBLY_RESULT

def get_group_search_query(group, result, accession):
    return PORTAL_SEARCH_BASE + get_group_query(accession) + '&' \
        + result + '&' + get_group_fields(group) + '&limit=0'

def get_experiment_search_query(run_accession):
    return PORTAL_SEARCH_BASE + 'query=run_accession="' + run_accession + '"' \
        + '&result=read_run&fields=experiment_accession&limit=0'

def print_error():
    print ('Something unexpected went wrong please try again.')
    print ('If problem persists, please contact datasubs@ebi.ac.uk for assistance.')