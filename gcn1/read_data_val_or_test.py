from parameters import *
import os, copy, json, sys, random
import nltk
import pickle
from read_data_util import *
from collections import *

data_type = sys.argv[1]
if data_type == 'val':
	data_dir = val_dir
else:
	data_dir = test_dir

vocab_dict = pickle.load(open(data_dump_dir+'vocab_word_to_id.pkl', 'rb'))

count = 0

#Files to write val/test data in readable form
open(data_dump_dir+data_type+"_contexts_image", 'w')
open(data_dump_dir+data_type+"_contexts_text", 'w')
open(data_dump_dir+data_type+"_targets_pos", 'w')
open(data_dump_dir+data_type+"_targets_negs", 'w')


#For each dialogue
for json_file in os.listdir(data_dir)[:]:
	#Load dialogue
	dialogue_json = json.load(open(data_dir+json_file))
	# print(len(dialogue_json))
	
	dialogue_till_now = []
	dialogue_targets_pos = []
	dialogue_targets_negs = []
	dialogue_contexts_text = []
	dialogue_contexts_image = []

	is_prev_utterance_a_question = False
	#For each utterance in dialogue
	for i, utterance_ in enumerate(dialogue_json):
		#print(i)
		utterance = utterance_['utterance'] #Textual part of utterance
		#print(utterance_)
		if utterance is None:
			continue					

		#Make an instance out of the dialogue till now, with last utterace as prediction
		if utterance_['speaker'] == "system" and is_prev_utterance_a_question == True and 'images' in utterance and not utterance['images'] == None and len(utterance['images'])>0 and 'false images' in utterance and not utterance['false images'] == None and len(utterance['false images'])>0  and not None in utterance['images'] and not None in utterance['false images']:
			
			padded_clipped_dialogue_instance = pad_or_clip_dialogue(dialogue_till_now)
			assert len(padded_clipped_dialogue_instance) == max_dialogue_len
			
			#Choose a positive target image
			sampled_img_pos = random.sample(utterance['images'],1)		
			dialogue_targets_pos.append(sampled_img_pos[0])
			#
	 		#Get negative images
			if use_random_neg_images == True:
				#Sample random numbers and get their URLs
				neg_indices = random.sample(range(total_images), num_neg_images_sample)
				dialogue_target_negs = [url_to_index_as_list[index][0] for index in neg_indices]
			else:
				#Get negative images from 'False Images' in the dataset itself
				if len(utterance['false images']) < num_neg_images_sample:
					pad_length = num_neg_images_sample - len(utterance['false images'])
					dialogue_target_negs = utterance['false images'] + ['RANDOM']*pad_length				
				elif len(utterance['false images']) > num_neg_images_sample:
					dialogue_target_negs = utterance['false images'][:num_neg_images_sample]
				else:
					dialogue_target_negs = utterance['false images']
			dialogue_targets_negs.append(dialogue_target_negs)		
			#
			#Textual and image context
			context_images = []
			context_texts = []
			for x in padded_clipped_dialogue_instance:
				if 'nlg' in x and x['nlg'] not in ["",None]:
					context_texts.append(x['nlg'])
				else:
					context_texts.append("")
				if 'images' in x and x['images'] is not None:
					context_images.append(x['images'])
				else:
					context_images.append([])
			dialogue_contexts_text.append(context_texts)
			dialogue_contexts_image.append(context_images)

			count += 1
			if count % 10000 == 0:
				print(count)

		#Is this utterance a question?
		if utterance_['type'] == 'question':	
			is_prev_utterance_a_question = True
		else:
			is_prev_utterance_a_question = False

		#Append context utterance instance
		inst = {}
		if 'images' in utterance:
			inst['images'] = utterance['images']
		if 'nlg' in utterance:
			inst['nlg'] = utterance['nlg']
		dialogue_till_now.append(inst)




	#Write all possible val/test cases from a single dialogue
	with open(data_dump_dir+data_type+"_contexts_text", 'a') as fp:
		for dialogue_context_text in dialogue_contexts_text:
			dialogue_context_text_write = '|'.join(dialogue_context_text)
			fp.write(dialogue_context_text_write.encode('utf-8')+'\n')	
	#
	with open(data_dump_dir+data_type+"_contexts_image", 'a') as fp:
		for dialogue_context_image in dialogue_contexts_image:
			dialogue_context_image_write = "^^^".join(["|".join(dialogue_context_each_image) for dialogue_context_each_image in dialogue_context_image])
			fp.write(dialogue_context_image_write+'\n')
	#
	with open(data_dump_dir+data_type+"_targets_pos", 'a') as fp:
		for dialogue_target_pos in dialogue_targets_pos:
	 		fp.write(dialogue_target_pos+'\n')
	#
	with open(data_dump_dir+data_type+"_targets_negs", 'a') as fp:
		for dialogue_target_negs in dialogue_targets_negs:
			dialogue_target_negs_write = '|'.join(dialogue_target_negs)
			fp.write(dialogue_target_negs_write+'\n')



#Now data is written, take it binarize it and store it
binarized = []
with open(data_dump_dir+data_type+"_targets_pos",) as targetposlines, open(data_dump_dir+data_type+"_targets_negs",) as targetnegslines, open(data_dump_dir+data_type+"_contexts_text") as textlines, open(data_dump_dir+data_type+"_contexts_image") as imagelines:
	for text_context, images_context, target_pos, target_negs in zip(textlines, imagelines, targetposlines, targetnegslines):
		
		#Binarize pos target
		binarized_target_pos = [target_pos.strip()]
		#
		#Binarize negative images
		binarized_target_negs = target_negs.strip().split('|')
		#
		#Binarize text context
		binarized_context_text = []
		utterances = text_context.lower().strip().split('|')
		for utterance in utterances:
			try:
				utterance_words = nltk.word_tokenize(utterance)
			except:
				utterance_words = utterance.split(' ')
			utterance_words = pad_or_clip_utterance(utterance_words)
			binarized_context_text.append([vocab_dict.get(word, unk_word_id) for word in utterance_words])
		#
		#
		#Binarize image context	
		actual_images_array = []	
		binarized_context_images = images_context.strip().split('^^^')
		#print(images_context, "concn")
		for ui in range(len(binarized_context_images)):
			if binarized_context_images[ui] == "":
				utterance_images  = []
			else:
				utterance_images = binarized_context_images[ui].strip().split("|")
			actual_num_images_in_context = len(utterance_images)
			actual_images_array.append(actual_num_images_in_context)
			binarized_context_images[ui] = utterance_images
			if actual_num_images_in_context < num_images_in_context:
				binarized_context_images[ui] += ["" for l in range(num_images_in_context - actual_num_images_in_context)]
		#print(np.array(binarized_context_images).shape)
		
		#Adjacency matrix
		adjacency = np.zeros((num_nodes, num_nodes))
		for x in range(max_context_len-1):
			adjacency[x*(num_images_in_context + 1)][(x+1)*(num_images_in_context + 1)] = 1
		for x in range(max_context_len):
			actual_num_images_in_context = actual_images_array[x]
			for i in range(actual_num_images_in_context):
				adjacency[x*(num_images_in_context+1)+i+1][x*(num_images_in_context+1)] = 1	
		sparse_adjacency = sparse.csr_matrix(adjacency)
		
		#Each training instance is appended
		binarized.append([binarized_context_text, binarized_context_images, sparse_adjacency, binarized_target_pos, binarized_target_negs])
print("Length of " + data_type + " data ", len(binarized))


print("pickling")
#Pickle binarized data
pickle_func(binarized, data_dump_dir+data_type+"_binarized_data.pkl")



				
	


