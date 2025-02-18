import os
import sys
import numpy

## Collect parameters
project_dir = ""
input_contig_dir = ""
contig_dir = ""
contig_extension = ""
output_prefix = ""
pop_infile_name = ""
ref_iso = ""
ref_contig = ""
focus_population = ""
len_block_threshold = 0
gap_prop_thresh = 0.0
window_size = 0
overlap = 0
MUGSY_source = ""
phyML_loc = ""
phyML_properties = ""
ape_loc = ""
percentile_threshold = 0.0
min_physplit_window_size = 0


parameter_file = open("phybreak_parameters.txt","r")
for line in parameter_file:
	line = line.strip().split(" = ")
	if len(line) > 1:
		if line[0] == "project_dir":
			project_dir = line[1].split(" #")[0]
		elif line[0] == "input_contig_dir":
			input_contig_dir = line[1].split(" #")[0]
		elif line[0] == "contig_dir":
			contig_dir = line[1].split(" #")[0]
		elif line[0] == "input_contig_extension":
			contig_extension = line[1].split(" #")[0]
		elif line[0] == "output_prefix":
			output_prefix = line[1].split(" #")[0]
		elif line[0] == "pop_infile_name":
			pop_infile_name = line[1].split(" #")[0]
		elif line[0] == "ref_iso":
			ref_iso = line[1].split(" #")[0]
		elif line[0] == "ref_contig":
			ref_contig = line[1].split(" #")[0]
		elif line[0] == "focus_population":
			focus_population = line[1].split(" #")[0]
		elif line[0] == "len_block_threshold":
			len_block_threshold = int(line[1].split(" #")[0])
		elif line[0] == "gap_prop_thresh":
			gap_prop_thresh = float(line[1].split(" #")[0])
		elif line[0] == "window_size":
			window_size = int(line[1].split(" #")[0])
		elif line[0] == "window_overlap":
			overlap = int(line[1].split(" #")[0])
		elif line[0] == "MUGSY_source":
			MUGSY_source = line[1].split(" #")[0]
		elif line[0] == "phyML_loc":
			phyML_loc = line[1].split(" #")[0]
		elif line[0] == "phyML_properties":
			phyML_properties = line[1].split(" #")[0]
		elif line[0] == "ape_loc":
			ape_loc = line[1].split(" #")[0]
		elif line[0] == "percentile_threshold":
			percentile_threshold = float(line[1].split(" #")[0])
		elif line[0] == "min_physplit_window_size":
			min_physplit_window_size = int(line[1].split(" #")[0])
parameter_file.close()

#these directories will generate if they do not already exist
input_dir = project_dir+"align/"
alignment_dir = input_dir+"alignment_blocks/"
phy_split_dir = input_dir+"phy_split/"
tree_dir = input_dir+"trees/"
msa_out_dir = input_dir+"phybreak_blocks/"

#these are output file names
strain_list_filename = "strain_names.txt"
MSA_name = output_prefix+".core.fasta"
LCB_info = output_prefix+".alignment_block_sizes.txt"
phy_prefix = output_prefix
block_loc_filename = output_prefix+".block_location.txt"
snp_loc_filename = output_prefix+".core.SNPloc.txt"
treeloc_filename = phy_prefix+".treeloc.txt"
tree_to_LCB_filename = "tree_to_LCB.txt"
lik_filename = phy_prefix+".phy_phyml_stat.txt"
Rscript_filename = "phybreak.leafdist_compare.R"
leaf_dist_file = output_prefix+".core.phyml_tree_info.leaf_dists.txt"
tree_info_file = phy_prefix+"_"+str(window_size)+".SNP_tree_summary.txt"
summary_file_name = "phybreak_result_"+focus_population+".txt"

#############   FUNCTIONS   #############

def tree_dist_sum(tree_in):
	tree_in = tree_in.replace(",(","$").replace(",","$").replace(")","$").split("$")
	sum_out = 0.0
	for i in range(0,len(tree_in)):
		if ":" in tree_in[i]:
			num = float(tree_in[i].split(":")[1])
			sum_out += num
	return sum_out

def msa_subset(seq_dict,strt,stp):
	seq_out = {}
	for iso in seq_dict:
		seq = seq_dict[iso][strt:stp+1]
		seq_out[iso] = seq
	return seq_out

#fills in space for phylip format sequence headers
def space_fill(text,length):
	num_spaces = length-len(text)
	spaces = ""
	for i in range(0,num_spaces):
		spaces += " "
	text_out = text+spaces
	return text_out

#writes MSA info in PHYLIP format
def fasta_2_phylip(seqs_dict,window_size):
	outseq = " "+str(len(seqs_dict))+" "+str(window_size)+"\n"
	head_dict = {}
	a=-1
	for header in seqs_dict:
		a += 1
		head_dict[a] = header
	for i in range(0,len(head_dict)):
		header = head_dict[i]
		outseq += space_fill(header,10)
		outseq += " "+ seqs_dict[header] + "\n"
	outseq += "\n"
	return outseq

def dict_to_fasta(seq_dict_in):
	out_string = ''
	for iso in seq_dict_in:
		out_string += ">"+iso+"\n"+seq_dict_in[iso]+"\n"
	return out_string

#############   MAIN   #############

##Make dictionary of strain to populations/groups
pop_infile = open(project_dir+pop_infile_name,"r")
pop_dict = {}
pop_list = []
for line in pop_infile:
	line = line.strip().split("\t")
	strain = line[0]
	pop = line[1]
	if strain != 'Strain':
		pop_dict[strain] = pop
		pop_list.append(pop)
pop_infile.close()
pop_list = list(set(pop_list))

##collate the distances in the leaf_dist output file
dist_dict = {}
max_dist_dict = {}
mono_phy_dict = {}
tree_no = 0
last_tree_no = 0
a = 0
strain_list = []
used = {}
all_pairwise_sum = {}
infile = open(input_dir+leaf_dist_file,"r")
for line in infile:
	line = line.strip()
	if line[0] == "#":
		tree_no = line.split("##")[1]
		monophy = line.split("##")[2]
		last_tree_no = int(tree_no)
		used = {}
		dist_dict[tree_no] = {}
		mono_phy_dict[tree_no] = monophy
		max_dist_dict[tree_no] = 0.0
		all_pairwise_sum[tree_no] = 0.0
		a = 1 #next line is horizontal list of strain names
	elif a == 1:
		strain_list = line.split("\t")
		a = 0
	else:
		iso1 = line.split("\t")[0]
		dists = line.split("\t")
		for i in range(1,len(dists)):
			iso2 = strain_list[i-1]
			if iso1 != iso2:
				pop1 = pop_dict[iso1]
				if pop1 == focus_population:
					pop1 = "focus"
				else:
					pop1 = "other"
				pop2 = pop_dict[iso2]
				if pop2 == focus_population:
					pop2 = "focus"
				else:
					pop2 = "other"
				pairF = iso1+"\t"+iso2
				pairR = iso2+"\t"+iso1
				pop_pairF = pop1+"\t"+pop2
				try:
					used[pairF]
				except:
					try:
						used[pairR]
					except:
						dist = float(dists[i])#/branch_sum_dict[tree_no]
						all_pairwise_sum[tree_no] += dist
						used[pairF] = ""
						used[pairR] = ""
						try:
							dist_dict[tree_no][pop_pairF].append(dist)
						except:
							dist_dict[tree_no][pop_pairF] = []
							dist_dict[tree_no][pop_pairF].append(dist)
						
						if dist > max_dist_dict[tree_no]:
							max_dist_dict[tree_no] = dist
infile.close()
del used
print("done iterating over leaf_dist file")

##Collect tree locations in the MSA
infile = open(input_dir+tree_info_file,"r")
tree_loc_info = {}
for line in infile:
	line = line.strip().split("\t")
	tree_no = line[0]
	msa_start = int(line[1])
	msa_stop = int(line[2])
	tree_loc_info[tree_no] = (msa_start,msa_stop)
infile.close()

##collect distances to calculate z-score
dict_collect = {}
for tree_no in dist_dict:
	for i in range(0,len(pop_list)):
		pop1 = pop_list[i]
		if pop1 == focus_population:
			pop1 = "focus"
		else:
			pop1 = "other"
		pop_pair = pop1+"\t"+pop1
		dist_list = dist_dict[tree_no][pop_pair]
		# rel_dist_list = []
		# for num in dist_list:
		# 	rel_dist_list.append(num)
		# avg = str(numpy.average(dist_list))
		dist_sum = str(numpy.sum(dist_list)/all_pairwise_sum[tree_no])
		try:
			dict_collect[pop_pair].append(dist_sum)
		except:
			dict_collect[pop_pair] = []
			dict_collect[pop_pair].append(dist_sum)
print("done collecting distances")

##Search the distances for max, min, and average distance within populations for each locus
percentile_dict = {}
physplit_trees = []
max_dist_counted = {}
focus_other_list = ['other','focus']
outfile = open(input_dir+summary_file_name,"w")
outfile.write("mid_point_of_window\ttree_no\tmonophy\tother\tother_percentile\tfocus\tfocus_percentile\tmono_phy_low_diversity\n")
for i in range(0,len(focus_other_list)):
	pop = focus_other_list[i]
	# print(pop)
	max_dist_counted[pop] = 0.0
dist_list = []
for j in range(1,last_tree_no+1): # in dist_dict:
	tree_no = str(j)
	mid_point_of_window = (tree_loc_info[tree_no][0]+tree_loc_info[tree_no][1])/2
	outfile.write(str(mid_point_of_window)+"\t"+tree_no+"\t"+mono_phy_dict[tree_no])
	min_percentile = 999.9
	for i in range(0,len(focus_other_list)):
		pop1 = focus_other_list[i]
		pop_pair = pop1+"\t"+pop1
		dist_list = dist_dict[tree_no][pop_pair]
		pop_dist_list = dict_collect[pop_pair]
		dist_sum = str(numpy.sum(dist_list)/all_pairwise_sum[tree_no])
		percentile = float(sum(x <= dist_sum for x in pop_dist_list))/float(len(pop_dist_list))
		outfile.write("\t"+dist_sum+"\t"+str(percentile))
		if percentile < min_percentile:
			min_percentile = percentile
			max_dist = (dist_sum,pop1)
	percentile_dict[tree_no] = min_percentile
	if min_percentile <= percentile_threshold and mono_phy_dict[tree_no] == "1":
		physplit_trees.append(tree_no)
		outfile.write("\t1")
		if max_dist[0] > max_dist_counted[max_dist[1]]:
			max_dist_counted[max_dist[1]] = max_dist[0]
	else:
		outfile.write("\t0")
	outfile.write("\n")
outfile.close()
outfile = open(input_dir+"max_distsum.txt","w")
for pop in max_dist_counted:
	outfile.write(pop +"\t"+ str(max_dist_counted[pop])+"\n")
outfile.close()
del dict_collect
del dist_dict
del max_dist_dict
del mono_phy_dict
del all_pairwise_sum

## Find regions that are most strongly divergent between populations
physplit_ranges = {}
range_num = 0
physplit_tree_count = 0
first_tree = ''
prev_stop = 0.0
prev_tree = ''
for i in range(1,last_tree_no+1):
	tree_no = str(i)
	msa_start = tree_loc_info[tree_no][0]
	msa_stop = tree_loc_info[tree_no][1]
	if tree_no not in physplit_trees or msa_start > prev_stop:
		prev_tree_status = False
		if physplit_tree_count >= min_physplit_window_size:
			range_num += 1
			physplit_ranges[range_num] = (first_tree,prev_tree)

			first_tree = ''
			physplit_tree_count = 0
		elif physplit_tree_count < min_physplit_window_size:
			first_tree = ''
			physplit_tree_count = 0
		if tree_no in physplit_trees:
			first_tree = tree_no
			physplit_tree_count = 1
			prev_tree_status = True
	elif tree_no in physplit_trees:
		if prev_tree_status == True:
			physplit_tree_count += 1
			prev_tree_status = True
		else:
			first_tree = tree_no
			physplit_tree_count = 1
			prev_tree_status = True
	#print(tree_no+"\t"+str(prev_tree_status)+"\t"+str(physplit_tree_count))
	prev_stop = msa_stop
	prev_tree = tree_no


##Store MSA in dictionary
infile = open(input_dir+MSA_name,"r")
head = ''
seq_dict = {}
for line in infile:
	line = line.strip()
	if line[0] == ">":
		head = line[1:len(line)]
	else:
		seq_dict[head] = line
infile.close()


if os.path.isdir(msa_out_dir) == False:
	os.makedirs(msa_out_dir)

print(physplit_ranges)
##Write range MSA to file and submit PhyML jobs
for range_num in physplit_ranges:
	tree_start = physplit_ranges[range_num][0]
	tree_stop = physplit_ranges[range_num][1]
	msa_start = tree_loc_info[tree_start][0]
	msa_stop = tree_loc_info[tree_stop][1]
	print(str(range_num)+"\t"+str(msa_start)+"\t"+str(msa_stop))
	msa_range_length = msa_stop-msa_start+1
	range_seq_dict = msa_subset(seq_dict,int(msa_start),int(msa_stop))
	
	#write MSA subset in fasta format
	fasta_string = dict_to_fasta(range_seq_dict)
	outfile = open(msa_out_dir+output_prefix+".block_"+str(range_num)+".fasta","w")
	outfile.write(fasta_string)
	outfile.close()

	#write MSA in phylip format and make a slurm file for making a ML tree from that alignment
	phylip_string = fasta_2_phylip(range_seq_dict,msa_range_length)
	outfile = open(msa_out_dir+output_prefix+".block_"+str(range_num)+".phy","w")
	outfile.write(phylip_string)
	outfile.close()
	phy_line = phyML_loc+" -i "+msa_out_dir+output_prefix+".block_"+str(range_num)+".phy -n 1 "
	phy_line += phyML_properties +" > "+msa_out_dir+output_prefix+".block_"+str(range_num)+".phy_phyml_stat.txt\n"
	os.system(phy_line)

