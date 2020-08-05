import sys
import json
import random
import os
import copy
import datetime 
import shutil
import logging
import pprint
import pathlib
import re
import subprocess
from contextlib import redirect_stdout
import time
import ntpath
import xml.etree.ElementTree as et
import itertools
from bs4 import BeautifulSoup
from itertools import combinations , product


class best_of_n_random (DailyBuildStrategy):

    def __init__(self, args):
        self.args = args
        self.name = 'best_of_n_random'
        # check the validity of the args
        # we expect to see two t1 and t2
        if ('t1' not in args) or ('t2' not in args):
            logger.fatal("FATAL: best_of_n_random strategy expects to have 't1' and 't2' as args.")

    def args_to_dir_name(self):
        return "t1_%s_t2_%s" % (str(self.args['t1']), str(self.args['t2']))
    
    def get_list_for_prioritize(self,alist,input_file):
        in_file=open(input_file,"r")
        for line in in_file:
            alist.append(line)
        in_file.close()
        return alist
    def create_last_temp_file(self,jennydict,temp_doc):
        f=open(temp_doc,"w+")
        size=len(jennydict)
        bad_chars=[",","'","[","]"]
        for x in range(size):
            line=str(jennydict[x])
            for char in bad_chars:
                line=line.replace(char,"")
            f.write(line+"\n")
        f.close()


    def convert_format(self,inputtxt,outputtxt,config_space_modell):
        in_file=open(inputtxt,"r")
        out_file=open(outputtxt,"w")
        bad_chars=[",","'","[","]"]
        for line in in_file:
            opt_count=0
            line_list=line.split()
            final_line=""
            for opt in config_space_modell['options']:
                opt_count=opt_count+1
                settings=str(opt["settings"])
                settings_list=settings.split(",")
                current_word=line_list[opt_count-1]
                current_word=str(current_word)
                current_word=current_word.replace(str(opt_count),"")
                number=ord(current_word)-97
                setting=settings_list[number]
                for char in bad_chars:
                    setting=setting.replace(char,"")
                final_line=final_line+setting+","
            final_line = final_line.rstrip(',')
            final_line=final_line.replace(" ","")  
            out_file.write(final_line)  
            out_file.write("\n")
        in_file.close()
        out_file.close()   

        
    def total_valid_tuple_count(self,paramList, t):
	    count = 0
	    for paramComb in combinations(paramList.keys(), t):
		    values = []
		    for par in paramComb:
			    values.append(paramList[par])
		    for valueComb in product(*values):
			    count += 1
	    return count
    def current_covered_tupples(self,jennydict,current,comb):
        for i in jennydict:
            list_temp=jennydict[i]
            list_temp1=tuple(combinations(jennydict[i],comb))
            for j in list_temp1:
                a = list(j)
                if current.count(a) == 0:
                    current.append(a)
        return len(current)
    
    def parse_input(self,inputfile,inputdict):
        f=open(inputfile , 'r')
        line = f.readline()
        for line in f:
            if line=="\n":
                break;
            line=line.rstrip()
            line1=line.split(':')
            line=line1[1].split(',')
            inputdict[line1[0]] = line
        f.close()
        return inputdict
    def parse_output(self,outputfile,jennydict):
        f=open(outputfile , 'r')
        count = 0
        for line in f:
            line=line.split()
            jennydict[count] = line
            count=count+1
        f.close()   
        return jennydict
    def run_jenny(self,inputfile,outputfile,t):
        jennyseed = random.randint(0 , 100000)
        f=open(inputfile,'r')
        line = f.readline()
        line = str(t)+" " + line
        command ="./jenny -n%s -s%d &> %s" % (line , jennyseed ,outputfile)
        to_run=open("run_jenny.txt","w")
        a=[]
        f.close()
        
        for word in command.split():
            a.append(str(word))
        for word2 in a:
            to_run.write(word2+" ")
        to_run.close()
        run_cmd(["bash","run_jenny.txt"])
        
        
        
        
        return None
    def create_jenny_format(self,config_space_modell,infile):
        out_file=open(infile,"w")
        characters_to_remove = "[]'" #chracters that will be removed from settings
        
                
        for opt2 in config_space_modell["options"]:
            settings2=str(opt2["settings"])
            parameter_no=settings2.count(",")+1
            out_file.write(str(parameter_no)+" ")
        out_file.write("\n") 
        for opt in config_space_modell['options']:
            option=str(opt["option"])
            out_file.write(option)
            settings=str(opt["settings"])
            
            
            for char in characters_to_remove: #remove forbidden from settings
                settings=settings.replace(char,"")
            
            
            out_file.write(": ")
            out_file.write(settings)
            out_file.write("\n")
        
        
        out_file.write("\n")
        out_file.close()
        return None   
    def generate_plan(self, sut, plan, strategy_plan_dir):

        # get the strategy arguments
        t1 = self.args['t1']
        t2 = self.args['t2']
        
        
        # get the configurations space model
        config_space_model = sut.get_config_space_model().get_model()
        run_cmd(["cp","./jenny",strategy_plan_dir])
        current_dir = os.getcwd()
        os.chdir(strategy_plan_dir)
        
        day_cnt = len(plan)
        
        number_of_arrays=1 #number of arrays
        
        
        input_dict={}
        
        all_table=[]
        
        self.create_jenny_format(config_space_model,"input.txt")
        cas=[]
        self.parse_input("input.txt",input_dict)
        totaltupple= self.total_valid_tuple_count(input_dict , t2)        
        
        for day in plan:
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            logger.info("     Generating a covering array for day %d..." % order)
            logger.info("        Output file: '%s'" % ca_out_file)
            
            most_new_array=0
            for array in range(number_of_arrays):                
                temp_dict={}
                temp_table=all_table
                self.run_jenny("input.txt" ,"output.txt",t1)
                self.parse_output("output.txt",temp_dict)
                no_covered_by_temp=self.current_covered_tupples(temp_dict,temp_table,t2)
                if no_covered_by_temp>most_new_array:
                    most_new_array=no_covered_by_temp
                    jennydict=temp_dict
                    all_table=temp_table
            self.create_last_temp_file(jennydict,"temp.txt")
            self.convert_format("temp.txt","for_priotirize.txt",config_space_model)
            daily_cas=[]
            daily_cas=self.get_list_for_prioritize(daily_cas,"for_priotirize.txt")
            cas.append(daily_cas)

        
        cas = self.priotrize_plan(cas, sut.get_config_space_model(), 
                            t2, strategy_plan_dir) 
        caidx=-1       
        for day in plan:
            caidx += 1
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            ca = cas[caidx]  
            with open(ca_out_file, 'w') as ca_file:
                for cfg in ca:
                    cfg_str = ''
                    for setting in cfg:
                        cfg_str += setting
                    cfg_str = re.sub('\,$', '', cfg_str)
                    ca_file.write(cfg_str + "\n")

        return None
        
class simple_portion_of_m_way (DailyBuildStrategy):

    def __init__(self, args):
        self.args = args
        self.name = 'simple_portion_of_m_way'
        # check the validity of the args
        # we expect to see two t1 and t2
        if ('t1' not in args) or ('t2' not in args):
            logger.fatal("FATAL: simple_portion_of_m_way strategy expects to have 't1' and 't2' as args.")

    def args_to_dir_name(self):
        return "t1_%s_t2_%s" % (str(self.args['t1']), str(self.args['t2']))
    
    def get_list_for_prioritize(self,alist,input_file):
        in_file=open(input_file,"r")
        for line in in_file:
            alist.append(line)
        in_file.close()
        return alist
    def write_to_final_cafile(self,in_file,out_file):
        infile=open(in_file,"r")
        outfile=open(out_file,"w")
        for x in range(7):
            infile.readline()
        for line in infile:
            outfile.write(line)
        infile.close()
        outfile.close()
        return None
    def give_seed(self,inputt,alist):
        f = open(inputt ,"a")
        for x in alist:
            f.write(x)
        f.close()
        return None
    
    def take_covering_array_portion(self,daily_no,outputt,alist,ignore):
        f = open(outputt)
        lock=False
        for x in range(7+ignore):
            f.readline()
        if(daily_no==-1):
            daily_no=5
            lock=True
            
        for y in range(daily_no):
            if(lock):
                daily_no=daily_no+1
            line=f.readline()
            if not line:
                break;
            alist.append(line)
        f.close()
        return alist
    
    def get_size_of_the_results(self,in_file):
        f = open(in_file,"r")
        size =-7
        while True:
            line=f.readline()
            size=size+1
            if not line:
                break;
        return size
        
    def run_acts(self,t,in_file,out_file):
        coverage="-Ddoi="+str(t)
        run_cmd(["java" ,coverage,"-Dmode=extend","-Doutput=csv","-jar","acts_3.2.jar",in_file,out_file])
        return None
    
    def create_acts_format(self,config_space_modell,infile):
        out_file=open(infile,"w")
        characters_to_remove = "[]'" #chracters that will be removed from settings
        characters_to_remove2 = "-."# characters that will be removed from options (acts doesnt allow those chars might need more for other suts)
        
        out_file.write("[System] \nName: X \n \n[Parameter]\n\n")
        
        
        for opt in config_space_modell['options']:
            option=str(opt["option"])#part we remove forbidden chars from option names
            option=option.replace("-","___")
            option=option.replace(".","____")
            out_file.write(option)
            settings=str(opt["settings"])
            
            
            for char in characters_to_remove: #remove forbidden from settings
                settings=settings.replace(char,"")
            
            if(settings.find("true")!=-1 or settings.find("TRUE")!=-1): #decide wheter it is boolean or enum 
                out_file.write(" (boolean) "+": ")
            elif(settings.isdigit()):
                out_file.write(" (int) "+": ")
            else:
                out_file.write(" (enum) "+": ")
            out_file.write(settings)
            out_file.write("\n")
        
        out_file.write("[Relation]\n\n") 
        out_file.write("[Constraint]\n\n")
        for cons in config_space_modell['constraints']:
            cons_str=str(cons)
            remove_char=["[",'"',"'","]",","]
            for char in remove_char:
                cons_str=cons_str.replace(char," ")
            count=-1
            cons_str=cons_str.replace("-","___")
            cons_str=cons_str.replace(".","____")
            cons_list=cons_str.split()
            final_string=""
            for word in cons_list:
                count=count+1
                if(count==0):
                    final_string=word+" = "
                elif(count==1):
                    if(word.isdigit()==True or word=="true" or word=="false"):
                        final_string= final_string + word +" => "
                    else:
                        final_string=final_string+'"'+word+'"'+" => "
                elif(count==2):
                    final_string=final_string+word+" != "
                else:
                    if(word.isdigit()==True or word=="true" or word=="false"):
                        final_string= final_string + word 
                    else:
                        final_string=final_string+'"'+word+'"'
            out_file.write(final_string+"\n")
            
           

               
        out_file.write("[Test Set]\n")
        test_set_parameters=""
        
        for opt in config_space_modell["options"]:
            test_set_parameters=test_set_parameters+str(opt["option"])+","
        
        test_set_parameters = test_set_parameters.rstrip(',')
        test_set_parameters=test_set_parameters.replace("-","___")
        test_set_parameters=test_set_parameters.replace(".","____")
        out_file.write(test_set_parameters)
        out_file.write("\n")
        out_file.close()
        return None
    def generate_plan(self, sut, plan, strategy_plan_dir):

        # get the strategy arguments
        t1 = self.args['t1']
        t2 = self.args['t2']

        # get the configurations space model
        config_space_model = sut.get_config_space_model().get_model() 
        run_cmd(["cp","./",strategy_plan_dir]) #copy acts into strategy directory
        
        current_dir = os.getcwd()
        os.chdir(strategy_plan_dir) #go to the strategy directory
        self.create_acts_format(config_space_model,"inputfile.txt") #create a file called inputfile.txt from acts format
        self.run_acts(t2,"inputfile.txt","output.txt") #build the desired m-way (m>n)
        daily_cas=[]
        size=self.get_size_of_the_results("output.txt")#get the number of test cases needed
        day_cnt = len(plan)
        ignore=0
        daily_number=10 #number of cases to be taken from m-way
        cas=[]
        for day in plan:
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            logger.info("     Generating a covering array for day %d..." % order)
            logger.info("        Output file: '%s'" % ca_out_file)
            daily_ca_list=[]
            
            self.take_covering_array_portion(daily_number,"output.txt",daily_ca_list,ignore)
            ignore=ignore+daily_number
            self.create_acts_format(config_space_model,"daily_input.txt")
            self.give_seed("daily_input.txt",daily_ca_list)
            self.run_acts(t1,"daily_input.txt","daily_output.txt")
            
            self.write_to_final_cafile("daily_output.txt","for_priotirize.txt")     
            daily_cas=[]
            daily_cas=self.get_list_for_prioritize(daily_cas,"for_priotirize.txt")
            cas.append(daily_cas)
            if(ignore>size):
                print("coverage got")
                ignore=0        
                self.run_acts(t2,"inputfile.txt","output.txt") #build the desired m-way (m>n)        
                size=self.get_size_of_the_results("output.txt")#get the number of test cases needed
        
        cas = self.priotrize_plan(cas, sut.get_config_space_model(), 
                            t2, strategy_plan_dir) 
        caidx=-1       
        for day in plan:
            caidx += 1
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            ca = cas[caidx]  
            with open(ca_out_file, 'w') as ca_file:
                for cfg in ca:
                    cfg_str = ''
                    for setting in cfg:
                        cfg_str += setting
                    cfg_str = re.sub('\,$', '', cfg_str)
                    ca_file.write(cfg_str )
        os.chdir(current_dir)
        return None   
class updated_portion_of_m_way(DailyBuildStrategy):

    def __init__(self, args):
        self.args = args
        self.name = 'updated_portion_of_m_way'
        # check the validity of the args
        # we expect to see two t1 and t2
        if ('t1' not in args) or ('t2' not in args):
            logger.fatal("FATAL: updated_portion_of_m_way strategy expects to have 't1' and 't2' as args.")

    def args_to_dir_name(self):
        return "t1_%s_t2_%s" % (str(self.args['t1']), str(self.args['t2']))
    def get_list_for_prioritize(self,alist,input_file):
        in_file=open(input_file,"r")
        for line in in_file:
            alist.append(line)
        in_file.close()
        return alist
    def give_seed_by_file(self,infile,outfile):
        with open(infile, 'r') as f:
            for line in f:
                with open(outfile,"a")as f2:
                    f2.write(line)
        f.close()
        f2.close()
        return None
    def return_size_of_prev(self,output):
        
        count = 0
        with open(output, 'r') as f:
            for line in f:
                count += 1
        f.close
        return count

    def write_to_final_cafile(self,in_file,out_file):
        infile=open(in_file,"r")
        outfile=open(out_file,"w")
        for x in range(7):
            infile.readline()
        for line in infile:
            outfile.write(line)
        infile.close()
        outfile.close()
        return None
    def give_seed(self,inputt,alist):
        f = open(inputt ,"a+")
        for x in alist:
            f.write(x)
        f.close()
        return None
    
    def take_covering_array_portion(self,daily_no,outputt,alist,ignore):
        f = open(outputt)

        for x in range(7+ignore):
            f.readline()
       
            
        for y in range(daily_no):
            line=f.readline()
            if not line:
                break;
            alist.append(line)
        f.close()
        return None
    
    
    def get_size_of_the_results(self,in_file):
        f = open(in_file,"r")
        size =-7
        while True:
            line=f.readline()
            size=size+1
            if not line:
                break;
        f.close()
        return size
        
    def run_acts(self,t,in_file,out_file):
        coverage="-Ddoi="+str(t)
        run_cmd(["java" ,coverage,"-Dmode=extend","-Doutput=csv","-jar","acts_3.2.jar",in_file,out_file])
        
        return None
    
    def create_acts_format(self,config_space_modell,infile):
        out_file=open(infile,"w")
        characters_to_remove = "[]'" #chracters that will be removed from settings
        characters_to_remove2 = "-."# characters that will be removed from options (acts doesnt allow those chars might need more for other suts)
        
        out_file.write("[System] \nName: X \n \n[Parameter]\n\n")
        
        
        for opt in config_space_modell['options']:
            option=str(opt["option"])#part we remove forbidden chars from option names
            option=option.replace("-","___")
            option=option.replace(".","____")
            out_file.write(option)
            settings=str(opt["settings"])
            
            
            for char in characters_to_remove: #remove forbidden from settings
                settings=settings.replace(char,"")
            
            if(settings.find("true")!=-1 or settings.find("TRUE")!=-1): #decide wheter it is boolean or enum 
                out_file.write(" (boolean) "+": ")
            elif(settings.isdigit()):
                out_file.write(" (int) "+": ")
            else:
                out_file.write(" (enum) "+": ")
            out_file.write(settings)
            out_file.write("\n")
        
        out_file.write("[Relation]\n\n") 
        out_file.write("[Constraint]\n\n")
        for cons in config_space_modell['constraints']:
            cons_str=str(cons)
            remove_char=["[",'"',"'","]",","]
            for char in remove_char:
                cons_str=cons_str.replace(char," ")
            count=-1
            cons_str=cons_str.replace("-","___")
            cons_str=cons_str.replace(".","____")
            cons_list=cons_str.split()
            final_string=""
            for word in cons_list:
                count=count+1
                if(count==0):
                    final_string=word+" = "
                elif(count==1):
                    if(word.isdigit()==True or word=="true" or word=="false"):
                        final_string= final_string + word +" => "
                    else:
                        final_string=final_string+'"'+word+'"'+" => "
                elif(count==2):
                    final_string=final_string+word+" != "
                else:
                    if(word.isdigit()==True or word=="true" or word=="false"):
                        final_string= final_string + word 
                    else:
                        final_string=final_string+'"'+word+'"'
            out_file.write(final_string+"\n")
            
           

               
        out_file.write("[Test Set]\n")
        test_set_parameters=""
        
        for opt in config_space_modell["options"]:
            test_set_parameters=test_set_parameters+str(opt["option"])+","
        
        test_set_parameters = test_set_parameters.rstrip(',')
        test_set_parameters=test_set_parameters.replace("-","___")
        test_set_parameters=test_set_parameters.replace(".","____")
        out_file.write(test_set_parameters)
        out_file.write("\n")
        out_file.close()
        return None   

    
    def generate_plan(self, sut, plan, strategy_plan_dir):

        # get the strategy arguments
        t1 = self.args['t1']
        t2 = self.args['t2']
        # get the configurations space model
        config_space_model = sut.get_config_space_model().get_model() 
        run_cmd(["cp","./acts_3.2.jar",strategy_plan_dir]) #copy acts into strategy directory
        current_dir = os.getcwd()
        os.chdir(strategy_plan_dir) #go to the strategy directory
        self.create_acts_format(config_space_model,"inputfile.txt") #create a file called inputfile.txt from acts format
        
        cas=[]
        total_CA_list=[]
        size_of_prev=0
        day_cnt = len(plan)
        ignore=0
        daily_number=10 #number of cases to be taken from m-way
        for day in plan:
            daily_ca_list=[]
            daily_ca_list2=[]
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            logger.info("     Generating a covering array for day %d..." % order)
            logger.info("        Output file: '%s'" % ca_out_file)
            
            self.run_acts(t2,"inputfile.txt","outputfile.txt")
            
            if ignore>=int(self.return_size_of_prev("outputfile.txt")-7):
                self.create_acts_format(config_space_model,"inputfile.txt")
                self.run_acts(t2,"inputfile.txt","outputfile.txt")
                ignore=0
            
            
            
            self.take_covering_array_portion(daily_number,"outputfile.txt",daily_ca_list,ignore)
            self.create_acts_format(config_space_model,"daily_in.txt")
            self.give_seed("daily_in.txt",daily_ca_list)
            daily_ca_list.clear()
            self.run_acts(t1,"daily_in.txt","daily_out.txt")   
            self.take_covering_array_portion(9999,"daily_out.txt",daily_ca_list2,0)
            self.write_to_final_cafile("daily_out.txt","for_priotirize.txt")
            total_CA_list=total_CA_list+daily_ca_list2


            size_of_prev=self.return_size_of_prev("for_priotirize.txt")
            ignore=ignore+size_of_prev
            self.give_seed_by_file("for_priotirize.txt","inputfile.txt")
            daily_cas=[]
            daily_cas=self.get_list_for_prioritize(daily_cas,"for_priotirize.txt")
            cas.append(daily_cas)
        
        cas = self.priotrize_plan(cas, sut.get_config_space_model(), 
                            t2, strategy_plan_dir) 
        caidx=-1       
        for day in plan:
            caidx += 1
            order = day['day']
            date = day['date']
            ca_out_file = day['ca_file']
            ca = cas[caidx]  
            with open(ca_out_file, 'w') as ca_file:
                for cfg in ca:
                    cfg_str = ''
                    for setting in cfg:
                        cfg_str += setting
                    cfg_str = re.sub('\,$', '', cfg_str)
                    ca_file.write(cfg_str )
        
        os.chdir(current_dir)
        return None       
# an example sut




class Flink (SUT):
    def __init__(self, config_space_model_file):
        SUT.__init__(self, "Flink", "1.0", config_space_model_file)
    
    def download(self, date_time, download_dir):        
        date_time_str = date_time.strftime("%m/%d/%Y") 
        hour_str = date_time.strftime("%H:%M:%S")
        # Download Cassandra
        run_cmd(['git', 'clone', 'https://github.com/apache/flink.git', download_dir])        
        path_to_pomxml = download_dir + os.sep + "pom.xml"
        if not os.path.exists(path_to_pomxml):
            return False
        shutil.copy("./checkout.flink",download_dir)
        current_dir = os.getcwd()  # store the current dir
        os.chdir(download_dir) # go to the download dir
        #chmod u+x checkout.flink
        run_cmd(["./checkout.flink", date_time_str, hour_str])
        os.chdir(current_dir) # go back to the current dir  
        return True
   
    def configure(self, cfg, static_config_found):
        self.set_curr_config(cfg)
        self.set_static_config_found(static_config_found)
        
        current_dir = os.getcwd()         
        working_dir = self.get_workdir()
        #run_cmd(["cp","./pom.xml.copy",working_dir])
        os.chdir(working_dir) # go to the working di
        
        pom=working_dir+os.sep+"pom.xml"
        pom_copy=pom+".copy"
        shutil.copy(pom, pom_copy)
        jacoco5="""<forkedProcessTimeoutInSeconds>3000</forkedProcessTimeoutInSeconds>
                       <forkedProcessExitTimeoutInSeconds>3000</forkedProcessExitTimeoutInSeconds>
                      <parallelTestsTimeoutInSeconds>3000</parallelTestsTimeoutInSeconds>
                    <parallelTestsTimeoutForcedInSeconds>3000</parallelTestsTimeoutForcedInSeconds> """
        #-Dmvn.surefire.timeout=1 
        jacoco3="<argLine>-Xms256m -Xmx2048m -Dmvn.forkNumber=${surefire.forkNumber"
        jacoco4="} -XX:+UseG1GC ${jacoco-coverage}</argLine>"
        in_file1=open(pom_copy,"r")
        out_file1=open(pom,"w")
        count=0
        #[67,71,72,79,83,85,89] -- original
        module_line=["<module>flink-quickstart</module>"]
        jococo="""<plugin>
<groupId>org.jacoco</groupId>
<artifactId>jacoco-maven-plugin</artifactId>
<version>0.8.2</version>
<configuration>
<destfile>${project.build.directory}/target/jacoco.exec</destfile>
</configuration>
<executions>
<!--  MODIFIED BY HANEFI  -->
<execution>
<id>default-prepare-agent</id>
<goals>
<goal>prepare-agent</goal>
</goals>
<configuration>
<propertyName>jacoco-coverage</propertyName>
</configuration>
</execution>
<execution>
<id>report</id>
<phase>test</phase>
<goals>
<goal>report</goal>
</goals>
</execution>
</executions>
</plugin>"""
        for line in in_file1:
            count=count+1
            if line.find("surefire for unit")!=-1:
                out_file1.write(jococo)
            elif line.find("<trimStackTrace>")!=-1:
                out_file1.write(line)    
                out_file1.write(jacoco5)
            elif line.find("-Dmvn.forkNumber=$")!=-1:
                out_file1.write(jacoco3+jacoco4)    
            elif (line in module_line)==False:
                out_file1.write(line)
            
            
                
        path_to_configuration_file = working_dir + os.sep + "flink-dist" + os.sep + "src" +os.sep + "main"+os.sep+"resources"+os.sep+"flink-conf.yaml"
        options = list(self.config_space_model.opt2idx.keys())
        
        
        out_file = open(path_to_configuration_file, "w")
        out_file.write("jobmanager.rpc.address: localhost \n")
        out_file.write("jobmanager.rpc.port: 6123 \n")
        out_file.write("jobmanager.memory.process.size: 1600m \n")
        out_file.write("taskmanager.memory.process.size: 1728m \n")
        out_file.write("taskmanager.numberOfTaskSlots: 1 \n") 
        out_file.write("parallelism.default: 1 \n")

        for option in options:
            if(option=="web.sumbit.enable:"):
                out_file.write("jobmanager.execution.failover-strategy: region \n")
            out_file.write(str(option)+": "+str(cfg[self.config_space_model.opt2idx[option]])+"\n")        
        out_file.close()
        out_file1.close()
        in_file1.close()
        os.chdir(current_dir)
        return True
    
    def build(self):
        current_dir = os.getcwd()  # store the current dir
        os.chdir(self.get_workdir()) # go to the working dir
        run_cmd(["mvn","-fn","package","-DskipTests","-Dmaven.test.failure.ignore=true"])
        #run_cmd(["cp","./build.log","/home/atakan/atakan/dailyBuildCaFramework"])
        os.chdir(current_dir) # go back to the current dir
        return True
    def run_tests(self):
        current_dir = os.getcwd()  # store the current dir
        work_dir=self.get_workdir()
        os.chdir(work_dir) # go to the working dir
        run_cmd(["mvn","-fn","test","-Dmaven.test.failure.ignore=true"])
        
        ind=0
        run_cmd(["mkdir","DailyBuild-jacoco_exec_files"])
        path_to_destination = work_dir+os.sep+"DailyBuild-jacoco_exec_files"
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                if file.endswith("jacoco.exec"):
                    jacoco_new_name="jacoco-"+str(ind)+".exec"
                    ind=ind+1
                    shutil.copy(os.path.join(root, file), path_to_destination+os.sep+jacoco_new_name)
        
        
        ind1=0
        run_cmd(["mkdir","DailyBuild-class_files"])
        path_to_destination2 =  work_dir+os.sep+"DailyBuild-class_files"
        class_names=[]
        for root, dirs, files in os.walk(work_dir):
            for file in files:
                class_name="example"+str(ind1)+".class"
                ind1=ind1+1
                if file.endswith(".class"):
                    shutil.copy(os.path.join(root, file), path_to_destination2+os.sep+class_name)
        
        
        jacocoli_path="/home/atakan/atakan/dailyBuildCaFramework/jacoco-0.8.5/lib/jacococli.jar"   
        merge_list=["java","-jar",jacocoli_path,"merge"]
    
        for a in range(ind):
            jacoco_new_name="jacoco-"+str(a)+".exec"
            merge_list.append(jacoco_new_name)
        merge_list.append("--destfile")
        merge_list.append("jacoco-merged.exec")
        os.chdir(work_dir+os.sep+"DailyBuild-jacoco_exec_files")
        run_cmd(merge_list)
       
        #below is hard coded path but it should work once the paths are changed
        #run_cmd(["java","-jar","/home/atakan/atakan/dailyBuildCaFramework/jacoco-0.8.5/lib/jacococli.jar","report","/home/atakan/atakan/dailyBuildCaFramework/Flink/work/DailyBuild-jacoco_exec_files/jacoco-merged.exec","--classfiles","/home/atakan/atakan/dailyBuildCaFramework/Flink/work/DailyBuild-jacoco_exec_files/DailyBuild-class_files/","--csv","results.csv"])
        
        os.chdir(current_dir) # go back to the current dir
        return True
    
    def daily_harvest(self, in_dir):
        
        
        return True

    def harvest_all(self, in_dir):
        
        return True

    def harvest_build_log(self, log_file):
        #TODO FIX
        return {'success':True}

    def harvest_configure_log(self, log_file):
        # TODO implement this
        return {'success':True}

    def harvest_tests_log(self, log_file):
               

        return {'success':True}

    def harvest_download_log(self, log_file):
        # How to understand whether download is failed from log_file?
        return {'success': True}

#jacocoli path is hard coded
#line that will give code coverage results is commented out because it has hard coded paths
#i tried to eleminate all the hard coded paths
#on simple and updated portion there is a variable called daily number which is the daily number of test cases it takes as portion
#on updated portion there is one called number_of_arrays which will be the number of arrays that will created to choose best one out of them
#system copies checkout.flink , jenny and acts by itself i suspect there might be problems due to problems
sut = 'Flink'
config_space_model_file = '/home/atakan/atakan/dailyBuildCaFramework/flink.model.txt'
start_date = datetime.datetime(2020, 6, 1, 23, 55, 0) # jan 1, 2020 at 23:55:00
end_date = datetime.datetime(2020, 6, 3, 23, 55, 0) # jan 3, 2020 at 23:55:00
archive_dir = '/home/atakan/atakan/dailyBuildCaFramework'

strategies = [{'name':'simple_portion_of_m_way', 'args':{'t1': 2, 't2':3}}]

run_experiment(sut, config_space_model_file,
               start_date, end_date,
               strategies,
               archive_dir)

# TODO:
# in build.xml file search for
#    Read all answers from here: https://stackoverflow.com/a/16690564
#    failonerror
#    maxmemory 
#    jvmarg

