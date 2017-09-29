import io
import os
import string
import csv
import zipfile
import pickle
import numpy as np
import pandas as pd

class DataProcessor(object):
    '''
    Class: DataProcessor
    
    Helper class that handles the details of processing the data files.
    Intended to be used by one of the prepare-data scripts on the local gpfs node.
    '''

    def __init__(self, gpfs_suffix):
        self.gpfs_suffix = gpfs_suffix
        self.gpfs_prefix = "/gpfs/gpfsfpo/"
        self.file_prefix = "googlebooks-eng-all-2gram-20090715-"
        self.file_headers = ["bi_gram", "year", "match_count", "page_count", "volume_count"]
        self.local_temp_folder_prefix = "/root/temp/"
        self.gpfs_path = self.gpfs_prefix + self.gpfs_suffix + "/"
        self.gpfs_counts_path = self.gpfs_prefix + self.gpfs_suffix + "/counts/"
    
    def delete_local_pickles(self):
        '''
        Deletes the pickled from the local temp folder on this gpfs node
        '''
        files = os.listdir(self.local_temp_folder_prefix)
        for f in files:
            if f.endswith(".pkl"):
                os.remove(os.path.join(self.local_temp_folder_prefix,f))
        print("deleted files from local temp:", len(files))
        

    def prep_file(self, file_suffix, nrows=None, chunk_size = 100000):
        '''
        Given a zip file suffix, constructs a dataframe of the bi-gram and its match-counts, e.g.
        
           bi_gram_0 bi_gram_1  match_count
        0  financial analysis   130
        1  financial capacity   75
        2  financial straits    53
        3  ...
        4  ...
        
        Because we can't assume bi-gram lists neatly ends on each file, this dataframe 
        needs to be combined with the results of all the other prepared files on this gpfs node
        for the gpfs node summary
        '''
        
        # will store the result here
        result = None

        # opens the zipped file and creates a panda based on the file
        with zipfile.ZipFile(self.gpfs_path + self.file_prefix + str(file_suffix) + ".csv.zip", "r") as z:
            with z.open(self.file_prefix + str(file_suffix) + ".csv", "r") as f:
                print("file:", file_suffix)
                f_txt = io.TextIOWrapper(f)
                # reads the data file into a data frame, in chunks
                chunk_counter = 0
                data_frames = pd.read_csv(
                    f_txt, 
                    sep='\t', 
                    lineterminator='\n', 
                    header=None, 
                    names=self.file_headers, 
                    chunksize=chunk_size, 
                    quoting=csv.QUOTE_NONE, 
                    nrows=nrows)
                
                # for each chunk in the file ...
                for frame in data_frames:
                    chunk_counter += 1
                    print("file:", file_suffix, "chunk:", chunk_counter)
                    
                    # splits the bi-gram into their own columns 
                    # also forces the bi-gram into lowercase
                    temp = frame["bi_gram"].str.lower().str.split(" ", expand=True)
                    # ... and strips leading & trailing punctuation
                    temp = temp.apply(lambda x : x.str.strip(string.punctuation))
                    if temp.shape[1] == 2:
                        # if the bi-gram has two words, adds the columns to the frame
                        frame[["bi_gram_0", "bi_gram_1"]] = temp
                    elif temp.shape[1] == 1:
                        # otherwise if the the bi-gram is just one word,
                        # then creates a second column of nulls
                        frame[["bi_gram_0"]] = temp
                        frame["bi_gram_1"] = ""
                    else:
                        raise ValueError("temp.shape[1] is not expected 1 or 2: ", temp.shape)
                    
                    # filters out any non-english words, defined as 
                    # bi-gram-0 is entirely alpha
                    # and bi-gram-1 is entirely alpha
                    filter1 = frame["bi_gram_0"].str.contains("^[A-Za-z]+$", na=False)
                    filter2 = frame["bi_gram_1"].str.contains("^[A-Za-z]+$", na=False)
                    frame = frame[filter1 & filter2]
                    
                    # groups by the bi-gram-0, bi-gram-1, and match_count columns, to save some space
                    frame = frame.groupby(["bi_gram_0", "bi_gram_1"])["match_count"].sum()
                    frame = pd.DataFrame({"match_count":frame}).reset_index()
                    
                    # and pickles the chunk, to save on memory
                    frame.to_pickle(self.local_temp_folder_prefix + str(file_suffix) + "_" + str(chunk_counter) + ".pkl")
                print("finished:", file_suffix)
                
    
    
    def concat_local_pickles(self):
        '''
        Unpickles and concatenates all the pickles in the local temp folder to calculate
        this gpfs node's summary. This calculates the final counts from all the files in 
        this gpfs node.
        
        It then pickles the final result to the counts folder in the gpfs.
                
        However, please note there is no guarantee that the bi-grams neatly fit within
        each server.
        '''
        
        # will store result in here
        result = None
        
        # gets the list of pickles from local temp
        local_pickles = os.listdir(self.local_temp_folder_prefix)
        
        # for each pickle in local temp ...
        for lp in local_pickles:
            if lp.endswith(".pkl"):
                with open(self.local_temp_folder_prefix + lp, "rb") as p:
                    # unpickles and concatenates to build a single dataframe that represents all the pickles
                    print("unpickling:", lp)
                    temp = pickle.load(p)
                    result = pd.concat([result, temp])
                    
        # groups by the bi-gram-0, bi-gram-1, and match_count columns, to save some space
        result = result.groupby(["bi_gram_0", "bi_gram_1"])["match_count"].sum()
        result = pd.DataFrame({"match_count":result}).reset_index()
        
        # pickles the dataframe to the gpfs, so that another script can use it
        node_summary_fullpath = self.gpfs_counts_path + "counts.pkl"
        print("pickling:", node_summary_fullpath)
        result.to_pickle(node_summary_fullpath)
