#!/usr/bin/env python
# The main script to manage the subworkflows of RASflow

import argparse
import os
import sys
import time
import yaml

def get_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(usage='%(prog)s [options]', description="Run an RNASeq analysis")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--qc', default=False, action="store_true", help='Run quality control')
    mode.add_argument('--trim', default=False, action="store_true", help='Run trimming')
    parser.add_argument('--logfile', default="logs/log_running_time.txt", help='Log file to write logs to')
    parser.add_argument('--config', default='configs/config_main.yaml', help='Config file to open')
    parser.add_argument('--project', help='Project to run')
    parser.add_argument('--reference', choices=["transcriptome", "genome"], help='Reference to use')
    parser.add_argument('--dea', default=False, action="store_true", help='Perform dea')
    parser.add_argument('--visualize', action="store_true", help='Perform visualization')
    args = parser.parse_args()
    return (args)

def spend_time(start_time, end_time):
    seconds = end_time - start_time
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hours, minutes, seconds)

def main():
    """Main function of the script"""
    args=get_args()
    # Parameters to control the workflow
    with open(args.config) as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.FullLoader)
    # Project
    if args.project:
        project = args.project
    else:
        project = config["PROJECT"]

     ## Do you want to visualize the results of DEA?
    if args.visualize:
        visualize = args.visualize
    else:
        visualize = config["VISUALIZE"]
    print(f"Visualization requested: {visualize}")
   
    # Start the workflow
    print("Start RASflow on project: " + project)
    
    ## write the running time in a log file
    file_log_time = open(args.logfile, "a+")
    file_log_time.write("\nProject name: " + project + "\n")
    file_log_time.write("Start time: " + time.ctime() + "\n")
   
    if args.qc:
        print("Starting Quality Control!")
        start_time = time.time()
        os.system("nice -5 snakemake -s workflow/quality_control.rules 2>&1 | tee logs/log_quality_control.txt")
        end_time = time.time()
        file_log_time.write("Time of running QC: " + spend_time(start_time, end_time) + "\n")
        print("Quality control is done!\n Please check the report and decide whether trimming is needed\n Please remember to turn off the QC in the config file!")
        sys.exit("QC finished, exiting the workflow")

    if args.trim:
        print("Start Trimming!")
        start_time = time.time()
        os.system("nice -5 snakemake -s workflow/trim.rules 2>&1 | tee logs/log_trim.txt")
        end_time = time.time()
        file_log_time.write("Time of running trimming:" + spend_time(start_time, end_time) + "\n")
        print("Trimming is done!")

    ### Mapping
    ## Which mapping reference do you want to use? Genome or transcriptome?
#FIXME
    if args.reference:
        reference = args.reference
    else:
        reference = config["REFERENCE"]
    print(f"Using {reference} reference\n")
  
    print("Starting to map reads using ", reference, " as reference!")
 
    if reference == "transcriptome":
        start_time = time.time()
        os.system("nice -5 snakemake -s workflow/quantify_trans.rules 2>&1 | tee logs/log_quantify_trans.txt")
        end_time = time.time()
        file_log_time.write("Time of running transcripts quantification:" + spend_time(start_time, end_time) + "\n")
    else: # reference == "genome" as only two choices are presented
        start_time = time.time()
        os.system("nice -5 snakemake -s workflow/align_count_genome.rules 2>&1 | tee logs/log_align_count_genome.txt")
        end_time = time.time()
        file_log_time.write("Time of running genome alignment:" + spend_time(start_time, end_time) + "\n")

    if args.dea:
        print("Starting DEA!")
        if reference == "transcriptome":
            start_time = time.time()
            os.system("nice -5 snakemake -s workflow/dea_trans.rules 2>&1 | tee logs/log_dea_trans.txt")
            end_time = time.time()
            file_log_time.write("Time of running DEA transcriptome based:" + spend_time(start_time, end_time) + "\n")
        else: # reference == "genome":
            start_time = time.time()
            os.system("nice -5 snakemake -s workflow/dea_genome.rules 2>&1 | tee logs/log_dea_genome.txt")
            end_time = time.time()
            file_log_time.write("Time of running DEA genome based:" + spend_time(start_time, end_time) + "\n")
        print("DEA is done!")
 
        if visualize:
            # Visualization can only be done on gene-level
            if reference == "transcriptome":
                gene_level = config["GENE_LEVEL"]
                if gene_level:
                    pass
                else:
                    print("Sorry! RASflow currently can only visualize on gene-level")
                    os._exit(1)
 
            print("Starting visualization of DEA results!")
            start_time = time.time()
            os.system("nice -5 snakemake -s workflow/visualize.rules 2>&1 | tee logs/log_visualize.txt")
            end_time = time.time()
            file_log_time.write("Time of running visualization:" + spend_time(start_time, end_time) + "\n")
            print("Visualization is done!")
            print("RASflow is done!")
        else:
            print("Visualization is not required and RASflow is done!")
    else:
             print("DEA is not required and RASflow is done!")
 
    file_log_time.write("Finish time: " + time.ctime() + "\n")
    file_log_time.close()
    
if __name__ == '__main__':
    main()
