#!usr/bin/python
from __future__ import division
from __future__ import print_function
from pyfaidx import Fasta
import re
import os.path as op
import glob

'''
dependent upon sqlite database containing annotations for OG and general identifiers for
OG and other databases used for annotation.  sqlite table located at: '/pool001/jbrown/blast_db.sqlite'
'''
#paths
prod_path="/nobackup1/jbrown/annotation/genes/"
faa_path="/nobackup1/jbrown/annotation/proteins/"

pfam_blast_path="/nobackup1/jbrown/annotation/blasts/Pfam/"
cog_blast_path="/nobackup1/jbrown/annotation/blasts/cogs_2003-2014/"
aclame_blast_path="/nobackup1/jbrown/annotation/blasts/aclame/"
cvp_blast_path="/nobackup1/jbrown/annotation/blasts/CVP/"
kegg_blast_path="/nobackup1/jbrown/annotation/blasts/kegg/"
tara_blast_path="/nobackup1/jbrown/annotation/blasts/tara.translated/"
egg_blast_path="/nobackup1/jbrown/annotation/blasts/eggnog/"
pog_blast_path="/nobackup1/jbrown/annotation/blasts/pog/"

def get_blast_paths(blastdir):
    '''returns [aclame_blast_path, cog_blast_path, cvp_blast_path, eggnog_blast_path, pfam_blast_path, pog_blast_path, tara_blast_path, keg_blast_path]'''
    dbnames=["aclame","cogs_2003-2014","CVP","eggnog","Pfam","pog","tara.translated","kegg"]
    return [op.join(blastdir, i) for i in dbnames]

def get_digits(faa):
    faa=open(faa).read()
    digits=len(str(faa.count(">")))
    return digits

def strip_lines_list(inlist):
    corrected=[i.replace("\n","") for i in inlist]
    return corrected

#create locus tag from protein sequence name in BLAST output file:
def get_locus_tag(line, digits, phage):
    query=line.split("\t")[0].split(" ")[0]
    number=query.split("_")[-1]
    z="0"*(digits-len(number))
    return "NVP"+phage.replace(".","")+"_"+z+number

def get_prot_lens(faa_file, phage):
    len_dict={}
    digits=get_digits(faa_file)
    #def make_seq_len_dict(faa):
    f=Fasta(faa_file)
    for i in f.keys():
        name=get_locus_tag(i, digits=digits, phage=phage)
        length=len(str(f[i]))
        len_dict[name]=length
    return len_dict

#set up dict of general info from BLAST:
def set_up_blast_dict(blast, prod, faa, phage, cov_thresh=75):
    digits=get_digits(faa)
    len_dict=get_prot_lens(faa, phage)
    records=[]
    blast_dict={}
    try:
        with open(blast) as ih:
            blast=ih.readlines()
            for line in blast:
                name=line.split(" ")[0]
                hit=line.split("\t")[1]
                lt=get_locus_tag(name, digits=digits, phage=phage)
                prot_len=len_dict[lt]
                aln_len=int(line.split("\t")[3])
                pct_id=float(line.split("\t")[2])
                ev=line.split("\t")[-2]
                pct_cov=(aln_len/prot_len)*100
                if pct_id>35 and pct_cov>cov_thresh and lt not in records:
                    records.append(lt)
                    blast_dict[lt]=[hit, pct_cov, pct_id, ev]
    except Exception as inst:
        print("could not open %s" %blast)
        print(inst)
    return blast_dict

#functions for adding annotations/info to BLAST hit based on BLAST database

#functions for adding annotations/info to BLAST hit based on BLAST database
from Bio.KEGG import REST
import sqlite3

###sqlite3 database checking functions:
def query_og1_tbl(qid, tbl, db_location='/pool001/jbrown/blast_db.sqlite'):
    conn=sqlite3.connect(db_location)
    c=conn.cursor()
    c.execute("SELECT OG from "+tbl+" where ID='"+qid+"'")
    output=c.fetchone()
    result=output[0]
    conn.close()
    return result

def query_og2_tbl(qid, tbl, db_location='/pool001/jbrown/blast_db.sqlite'):
    conn=sqlite3.connect(db_location)
    c=conn.cursor()
    c.execute("SELECT function from "+tbl+" where OG='"+qid+"'")
    output=c.fetchone()
    result=output[0]
    conn.close()
    return result

def query_og3_tbl(qid, tbl, db_location='/pool001/jbrown/blast_db.sqlite'):
    conn=sqlite3.connect(db_location)
    c=conn.cursor()
    c.execute("SELECT category from "+tbl+" where ID='"+qid+"'")
    output=c.fetchone()
    result=output[0]
    conn.close()
    return result

def query_func_tbl(qid, tbl, db_location='/pool001/jbrown/blast_db.sqlite'):
    conn=sqlite3.connect(db_location)
    c=conn.cursor()
    c.execute("SELECT function from "+tbl+" where ID='"+qid+"'")
    output=c.fetchone()
    result=output[0]
    conn.close()
    return result

def query_phy_tbl(qid, tbl, db_location='/pool001/jbrown/blast_db.sqlite'):
    conn=sqlite3.connect(db_location)
    c=conn.cursor()
    c.execute("SELECT phy1, phy2, phy3 from "+tbl+" where ID='"+qid+"'")
    output=c.fetchone()
    result=output
    conn.close()
    return result

##shorten excessively long protein descriptions:
def reduce_func_len(function):
    if len(function)>50:
        if function.split(",")>1:
            function=function.split(",")[0]
        elif function.split(";")>1:
            function=function.split(";")[0]
        elif function.split(".")>1:
            function=function.split(".")[0]
        else:
            function=function[0:50]
    else:
        function=function
    return function

###find go and functional annotations based on BLAST identifier:
def add_kegg_descript(hit):
    try:
        desc= REST.kegg_find("genes", hit).read()
        try:
            K=re.search(r"K[0-9]{5}", desc)
            KEGG=K.group(0)
        except:
            KEGG="none"
        try:
            a=re.search(r"(?<=K[0-9]{5}).*", desc).replace("\n","")
            ann=a.group(0)
        except:
            try:
                ann=desc.split("\t")[1].split(";")[0].replace("\n","")
            except:
                ann="none"
    except:
        ann="none"
        KEGG="none"
    ann=reduce_func_len(ann)
    return strip_lines_list([KEGG, ann])

def add_kegg_descript2(hit):
    try:
        desc= REST.kegg_find("genes", hit).read()
        try:
            K=re.search(r"K[0-9]{5}", desc)
            KEGG=K.group(0)
        except:
            KEGG="none"
        try:
            a=re.search(r"(?<=K[0-9]{5}).*", desc).replace("\n","")
            ann=a.group(0)
        except:
            try:
                ann=desc.split("\t")[1].split(";")[0].replace("\n","")
            except:
                ann="none"
        try:
            mod=REST.kegg_link('module', hit).read()
            module=mod.split(":")[2].split("_")[-1].replace("\n","")
        except:
            module="none"

    except:
        module="none"
        KEGG="none"
        ann="none"
    ann=reduce_func_len(ann)
    return strip_lines_list([module, KEGG, ann])

def add_cog_descript(hit):
    cog=query_og1_tbl((hit.split("|")[1]),"cog1")
    func=query_og2_tbl(cog,"cog2").replace("\n","")
    func=reduce_func_len(func)
    return strip_lines_list([cog, func])

def add_pfam_descript(hit):
    pfam=query_og1_tbl(hit,"pfam1").split(".")[0]
    function=query_og2_tbl(pfam, "pfam2").replace("\n","")
    function=reduce_func_len(function)
    return strip_lines_list([pfam, function])

def add_aclame_descript(hit):
    annotation=query_func_tbl(hit, "aclame")
    annotation=reduce_func_len(annotation)
    return strip_lines_list([hit, annotation])

def add_cvp_descript(hit):
    func=query_func_tbl(hit, "cvp")
    func=reduce_func_len(func)
    return strip_lines_list([hit, func])

def add_egg_descript(hit):
    try:
        og=query_og1_tbl(hit, "egg1")
        func=query_og2_tbl(og, "egg2")
    except:
        og="none"
        func="none"
    func=reduce_func_len(func)
    return strip_lines_list([og, func])

def add_egg_descript2(hit):
    try:
        og=query_og1_tbl(hit, "egg1")
        func=query_og2_tbl(og, "egg2")
        cat=query_og3_tbl(hit, "egg1")
    except:
        og="none"
        func="none"
        cat="none"
    func=reduce_func_len(func)
    return strip_lines_list([cat, og, func])

def add_tara_descript(hit):   #right now just adding the closest hit, TARA sequences come with COG/Pfam info etc
    return strip_lines_list([hit, hit])

def add_pog_descript(hit):
    og=query_og1_tbl(hit.split("|")[1], "pog")
    function=query_og2_tbl(og, "pog")
    function=reduce_func_len(function)
    return strip_lines_list([og, function])

def add_pog_descript2(hit):
    og=query_og1_tbl(hit.split("|")[1], "pog")
    function=query_og2_tbl(og, "pog")
    function=reduce_func_len(function)
    phylog=query_phy_tbl(hit.split("|")[1],"pog")
    phylist=[i.split("]")[-1] for i in phylog]
    return strip_lines_list([og, function]+phylist)

def annotated_blast_dict(blast, prod, faa, db, phage, cov_thresh=75):
    db_dict={"kegg":add_kegg_descript,
         "cog":add_cog_descript,
         "pfam":add_pfam_descript,
         "aclame":add_aclame_descript,
         "cvp":add_cvp_descript,
         "tara":add_tara_descript,
         "egg":add_egg_descript,
         "pog":add_pog_descript}

    blast_dict=set_up_blast_dict(blast, prod, faa, phage, cov_thresh=cov_thresh)
    blast_db_function=db_dict[db]
    for i in blast_dict.keys():
        hit=blast_dict[i][0]
        info=blast_db_function(hit)
        blast_dict[i]+=info
    return blast_dict

def enhanced_blast_dict(blast, prod, faa, db, phage, cov_thresh=75):
    db_dict={"kegg":add_kegg_descript2,
         "egg":add_egg_descript2,
         "pog":add_pog_descript2}

    blast_dict=set_up_blast_dict(blast, prod, faa, phage, cov_thresh=cov_thresh)
    blast_db_function=db_dict[db]
    for i in blast_dict.keys():
        hit=blast_dict[i][0]
        info=blast_db_function(hit)
        blast_dict[i]+=info
    return blast_dict

#load blast files for genome into dict of blast results
def load_blast_files(phage, prod_path, faa_path, blast_path, cov_thresh=75):
    '''
    >> load_blast_files('1.028.O', '/nobackup1/jbrown/newmu/genes/', '/nobackup1/jbrown/newmu/proteins/', '/nobackup1/jbrown/newmu/blast/')
    could not open /nobackup1/jbrown/newmu/blasts/Pfam/2.159.B.vs.pfam.out
    could not open /nobackup1/jbrown/newmu/blasts/cogs_2003-2004/2.159.B.vs.cogs_2003-2014.out
                   blast = '/nobackup1/jbrown/newmu/blasts/cogs_2003-2004/2.159.B.vs.cogs_2003-2004.out'
    '''
    prod=op.join(prod_path,phage+".gene")
    faa=glob.glob(op.join(faa_path,phage+"*.f*a"))[0]
    print("using {} as the protein file".format(faa))

    [aclame_blast_path, cog_blast_path, cvp_blast_path, eggnog_blast_path, pfam_blast_path, pog_blast_path, tara_blast_path, keg_blast_path] = get_blast_paths(blast_path)

    cog_blast=op.join(cog_blast_path,phage+".vs.cogs_2003-2014.out")
    aclame_blast=op.join(aclame_blast_path,phage+".vs.aclame.out")
    cvp_blast=op.join(cvp_blast_path,phage+".vs.CVP.out")
    kegg_blast=op.join(kegg_blast_path,phage+".vs.kegg.out")
    tara_blast=op.join(tara_blast_path,phage+".vs.tara.translated.out")
    egg_blast=op.join(egg_blast_path,phage+".vs.eggnog.out")
    pog_blast=op.join(pog_blast_path,phage+".vs.pog.out")
    pfam_blast = op.join(pfam_blast_path, phage+".vs.Pfam.out")

    kegg_blast_dict=annotated_blast_dict(blast=kegg_blast, prod=prod, faa=faa, db="kegg", phage=phage, cov_thresh=cov_thresh)
    pfam_blast_dict=annotated_blast_dict(blast=pfam_blast, prod=prod, faa=faa, db="pfam", phage=phage, cov_thresh=cov_thresh)
    cog_blast_dict=annotated_blast_dict(blast=cog_blast, prod=prod, faa=faa, db="cog", phage=phage, cov_thresh=cov_thresh)
    aclame_blast_dict=annotated_blast_dict(blast=aclame_blast, prod=prod, faa=faa, db="aclame", phage=phage, cov_thresh=cov_thresh)
    cvp_blast_dict=annotated_blast_dict(blast=cvp_blast, prod=prod, faa=faa, db="cvp", phage=phage, cov_thresh=cov_thresh)
    tara_blast_dict=annotated_blast_dict(blast=tara_blast, prod=prod, faa=faa, db="tara", phage=phage, cov_thresh=cov_thresh)
    egg_blast_dict=annotated_blast_dict(blast=egg_blast, prod=prod, faa=faa, db="egg", phage=phage, cov_thresh=cov_thresh)
    pog_blast_dict=annotated_blast_dict(blast=pog_blast, prod=prod, faa=faa, db="pog", phage=phage, cov_thresh=cov_thresh)

    blasts={"kegg":kegg_blast_dict,
            "pfam":pfam_blast_dict,
            "cog":cog_blast_dict,
            "aclame":aclame_blast_dict,
            "cvp":cvp_blast_dict,
            "tara":tara_blast_dict,
            "egg":egg_blast_dict,
            "pog":pog_blast_dict}
    return blasts

def load_kegg_egg_pog_blast(phage, cov_thresh=75):
    prod=op.join(prod_path,phage+".gene")
    faa=op.join(faa_path,phage+".faa")

    [aclame_blast_path, cog_blast_path, cvp_blast_path, eggnog_blast_path, pfam_blast_path, pog_blast_path, tara_blast_path, keg_blast_path] = get_blast_paths(blast_path)

    kegg_blast=kegg_blast_path+phage+"vs.kegg.out"
    egg_blast=egg_blast_path+phage+"vs.eggnog.out"
    pog_blast=pog_blast_path+phage+"vs.pog.out"

    kegg_blast_dict=enhanced_blast_dict(blast=kegg_blast, prod=prod, faa=faa, db="kegg", phage=phage, cov_thresh=cov_thresh)
    egg_blast_dict=enhanced_blast_dict(blast=egg_blast, prod=prod, faa=faa, db="egg", phage=phage, cov_thresh=cov_thresh)
    pog_blast_dict=enhanced_blast_dict(blast=pog_blast, prod=prod, faa=faa, db="pog", phage=phage, cov_thresh=cov_thresh)

    blasts={"kegg":kegg_blast_dict,
            "egg":egg_blast_dict,
            "pog":pog_blast_dict}
    return blasts
