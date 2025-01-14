# -*- coding: utf-8 -*-
"""
Created on Tue Jan 18 06:42:07 2022

@author: anddy
"""

import requests, json
import numpy as np
import random as random
from datetime import date
from datetime import datetime
import sys, os
if os.name == 'posix':
    sys.path.append('/Users/andylee/Desktop/git_prepFile')
else:
    sys.path.append('C:\\NotionUpdate\\progress')

from secret import secret
import pandas as pd

token = secret.vocab("token")
databaseId = secret.vocab("databaseId")
headers = {
    "Authorization": "Bearer " + token,
    "Content-Type": "application/json",
    "Notion-Version": "2021-05-13"
}

# Set total number of vocabulary suggestions & Exposures
total_vocab_sug = 5
total_exposures = 6

class Connect_Notion:
    
    def is_time_between(begin_time, end_time, check_time=None):
        # If check time is not given, default to current UTC time
        check_time = check_time or datetime.now().time()
        if begin_time < end_time:
            return check_time >= begin_time and check_time <= end_time
        else: # crosses midnight
            return check_time >= begin_time or check_time <= end_time
        
        
    def readDatabase(self, databaseId, headers):
        readUrl = f"https://api.notion.com/v1/databases/{databaseId}/query"
    
        res = requests.request("POST", readUrl, headers=headers)
        data = res.json()
        # print(res.text)
    
        with open('./db.json', 'w', encoding='utf8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        return data
    
    
    def get_projects_titles(self,data_json):
        most_properties = [len(data_json['results'][i]['properties'])
                                for i in range(len(data_json["results"]))]
        return list(data_json["results"][np.argmax(most_properties)]["properties"].keys())+['pageId']
    
    def get_projects_data(self, data, projects):
        projects_data = {}
        for p in projects:
            if "Vocab" in p:
                projects_data[p] = [data['results'][i]['properties'][p]['title'][0]['text']['content']
                                    for i in range(len(data["results"]))]
            elif p == 'Source':
                projects_data[p] = [data['results'][i]['properties'][p]['multi_select'][0]['name']
                                    for i in range(len(data["results"]))]
            elif p=="Count":
                projects_data[p] = [data['results'][i]['properties'][p]['number']
                                    for i in range(len(data["results"]))]
            elif p=="Next":
                projects_data[p] = [data['results'][i]['properties'][p]['select']['name']
                                    for i in range(len(data["results"]))]
            elif p=="Conscious":
                projects_data[p] = [data['results'][i]['properties'][p]['checkbox']
                                    for i in range(len(data['results']))]
            elif p=="pageId":
                projects_data[p] = [data['results'][i]['id']
                                    for i in range(len(data["results"]))]
            elif p=="Last_Edited":
                last_edited_dates = []
                for i in range(len(data["results"])):
                    date = datetime.fromisoformat(data['results'][i]['properties'][p]['last_edited_time'][:-1] + '+00:00')
                    date = date.strftime('%Y-%m-%d')
                    last_edited_dates.append(date)       
                projects_data[p] = last_edited_dates
        return projects_data
    
    
    # Notion API limits a list result of 100 elements next_page() helps retrieve ALL data
    def next_page(self, data):
        readUrl = f"https://api.notion.com/v1/databases/{databaseId}/query"
        next_cur = data['next_cursor']
        try:
            while data['has_more']:
                data['start_cursor'] = next_cur
                data_hidden = json.dumps(data)
                data_hidden = requests.post(readUrl, headers= headers, data= data_hidden).json() # Gets the next 100 results
    
                
                next_cur = data_hidden['next_cursor']
                
                data["results"] += data_hidden["results"]
                if next_cur is None:
                    break
        except:
            pass
        return data

        
        
    def updateData_to_next(pageId, headers):
        updateUrl_to_next = f"https://api.notion.com/v1/pages/{pageId}"
    
        updateData_to_next = {
            "properties": {
                "Next": {
                    "select": 
                        {
                                "name": "Next"
                        }
                }        
            }
        }
        
        
        response = requests.request("PATCH", updateUrl_to_next, 
                                    headers=headers, data=json.dumps(updateData_to_next))
    
    def updateData_to_waitlist(pageId, headers):
        updateUrl_to_waitlist = f"https://api.notion.com/v1/pages/{pageId}"
    
        updateData_to_waitlist = {
            "properties": {
                "Next": {
                    "select": 
                        {
                                "name": "Wait List"
                        }
                }        
            }
        }
        
        
        response = requests.request("PATCH", updateUrl_to_waitlist, 
                                    headers=headers, data=json.dumps(updateData_to_waitlist))
            
    def updateData_count(count_min,pageId, headers):
        updateUrl_to_waitlist = f"https://api.notion.com/v1/pages/{pageId}"
        updateData_count = {
            "properties": {
                "Count": {
                                "number": count_min +1
            }
        }}
        
        
        response = requests.request("PATCH", updateUrl_to_waitlist, 
                                    headers=headers, data=json.dumps(updateData_count))
        
    def move_to_conscious(pageId, headers):
        # After reaching 7 exposures, the vocabulary will moved to other DB, called "conscious"
        updateUrl_to_waitlist = f"https://api.notion.com/v1/pages/{pageId}"
        updateData_count = {
            "properties": {
                "Conscious": {
                                "checkbox": True
            }
        }}
        
        
        response = requests.request("PATCH", updateUrl_to_waitlist, 
                                    headers=headers, data=json.dumps(updateData_count))
        


    def adjust_suggestionRate(self, projects_data, total_vocab_sug):
        
        adj_suggest_rate = 18
        
        # The purpose for this function is to find an appropriate rate for daily suggestions.
        # This is to prevent congestion caused by too many vocabs on the waitlist compared to 
        # the vocabs being suggested. 
        
        vocab_df = pd.DataFrame(projects_data)
        
        # Get total number of vocabs waiting to be suggested
        tot_vocab_watiList = len(vocab_df[vocab_df['Conscious'] == False])
        
        # If the waitlist is over 100, adjust the suggestion rate 
        if tot_vocab_watiList > 100:
            total_vocab_sug = round(tot_vocab_watiList / adj_suggest_rate)
        else:
            pass
        
        return total_vocab_sug
        

    def execute_update(self, projects_data, headers):
        # Find where next indexes are
        today_index = [i for i in range(len(projects_data['Vocab']))
                       if projects_data["Next"][i]=="Next"]
        # Find page Ids that matches Next's indexes
        today_pageId = [projects_data["pageId"][i] for i in today_index
                        if projects_data["Next"][i]=="Next"]
        
        today_count = [projects_data["Count"][i] for i in today_index
                        if projects_data["Next"][i]=="Next"]
        
        count_min = min(projects_data['Count'])
        
        
        new_selection_index = []
        must_review_vocabs = []
        
        print()
        print("Updating Vocabs...")
        # Find new vocabs with lowest count
            # count_min: lowest count
            # Conscious == False: Unmemorized vocab
            # not in next_index: suggest different words than the day before
            # not in new_source: suggest unique 3 words
        c = 0
        least_count = count_min
        while True:
            if len(projects_data['Vocab']) < c + 1 and count_min == np.max(projects_data['Count']):
                break
            try:
                if projects_data['Count'][c] == count_min and \
                   projects_data['Conscious'][c]==False and \
                   c not in new_selection_index and \
                   c not in today_index and \
                   date.today().strftime('%Y-%m-%d') != projects_data['Last_Edited'][c]:
                    
                    new_selection_index.append(c)
            except:
                c = 0

                # least_count == 1: Recently added, so add maximum 3 to must_review list
                if (least_count == 1 or least_count == 0) and len(new_selection_index) < 4:
                    must_review_vocabs = new_selection_index
                elif (least_count == 1 or least_count == 0) and len(new_selection_index) >= 4:
                    must_review_vocabs = new_selection_index[:2]
                else:
                    pass
                count_min += 1                    
            c += 1
        
        # random number between 0 to total length of vocabularies with the minimum count
        if len(new_selection_index) == total_vocab_sug:
            pass
        else:
            random_vocabs = []
            
            # If must_review_vocabs is not empty, add them first before adding other vocabularies
            if must_review_vocabs != []:
                random_vocabs = must_review_vocabs
                
            # Run as many times to satisfy 3 random words from the new_selection pool
            while True:
                ind = random.choices(new_selection_index)
                if len(random_vocabs) > total_vocab_sug-1:
                    break
                if ind[0] not in random_vocabs:
                    random_vocabs.append(ind[0])
            new_selection_index = random_vocabs

        # select a new vocab pageId randomly 
        new_selection_pageId = [projects_data['pageId'][i] for i in new_selection_index]
        
        # Store new & old vocabulary information for the Slack update
        new_selection_vocab = []
        new_selection_source = []
        new_selection_count = []
        today_vocabs = []
        today_source = []
        today_count = []
        
        for i in range(total_vocab_sug):
            # Prevent an error caused by changing the total number of vocab suggestions
            try:
                new_selection_vocab.append(projects_data['Vocab'][new_selection_index[i]])
                new_selection_source.append(projects_data['Source'][new_selection_index[i]])
                new_selection_count.append(projects_data['Count'][new_selection_index[i]])
                today_vocabs.append(projects_data['Vocab'][today_index[i]])
                today_source.append(projects_data['Source'][today_index[i]])
                today_count.append(projects_data['Count'][today_index[i]])
            except:
                pass
        
        print('new_selection_vocab: ',new_selection_vocab)
        print('today_vocabs: ', today_vocabs)
        print()
        # Update Notion 
            # 1. Change next -> Waitlist
            # 2.Change Waitlist -> next
            # 3. Update count +1 
                # If the exposure count reaches 7, move to conscious DB
        for i in range(len(new_selection_vocab)):
            print("Updating : [", new_selection_vocab[i], "]")
            
            # Send the learned vocabs back to waitlist
            try:
                Connect_Notion.updateData_to_waitlist(today_pageId[i], headers)
            except:
                pass
            
            # Update new selected vocabs
            try:
                Connect_Notion.updateData_to_next(new_selection_pageId[i], headers)
            except:
                pass
            
            # If the vocab count reaches assigned total_exposure, send it to a separate DB
            try:
                if today_count[i] >= total_exposures:
                    Connect_Notion.move_to_conscious(today_pageId[i], headers)
                Connect_Notion.updateData_count(today_count[i], today_pageId[i], headers)
            except:
                pass
            print("Completed\n")
        

        
        return today_vocabs, today_source, today_count

    
    def connect_LinguaAPI(self, vocabs, api_key):

        vocab_dic = {}
        for vocab in vocabs:
            url = "https://lingua-robot.p.rapidapi.com/language/v1/entries/en/" + vocab.lower().strip(' ')
            headers = {
            	"X-RapidAPI-Key": api_key,
            	"X-RapidAPI-Host": "lingua-robot.p.rapidapi.com"
            }
            
            response = requests.request("GET", url, headers=headers)
            data = json.loads(response.text)

            

            # DEFINE vocab_info
            # try: Some vocabuarlies do not have definitions (ex: fugazi)
            try:
                vocab_dat = data['entries'][0]['lexemes']
            except IndexError:
                vocab_dat = None
                definitions = None
                synonyms = None
                examples = None
            
            if vocab_dat != None:
                # GET DEFINITIONS
                # try: If the definition is not in Lingua Dictionary, output None
            
                definitions = [vocab_dat[j]['senses'][i]['definition']
                               for j in range(len(vocab_dat)) for i in range(len(vocab_dat[j]['senses']))]
                definitions = definitions[:3]
            
                
                # GET SYNONYMS
                # try: If synonyms are not in Lingua Dictionary, output None
                try:
                    synonyms = [vocab_dat[j]['synonymSets'][i]['synonyms']
                                for j in range(len(vocab_dat)) for i in range(len(vocab_dat[j]['synonymSets']))]
                except KeyError:
                    synonyms = None
                
                # GET EXAMPLES
                try:
                    examples = [vocab_dat[j]['senses'][i]['usageExamples']
                            for j in range(len(vocab_dat)) for i in range(len(vocab_dat[j]['senses'])) \
                            if 'usageExamples' in vocab_dat[j]['senses'][i].keys()]
                except:
                    examples = None
            vocab_dic.setdefault(vocab,[]).append({'definitions':definitions,
                                                   'examples':examples,
                                                   'synonyms':synonyms})
        return vocab_dic
            


    # Send a Message using Slack API
    def send_vocab(self, vocabs, definitions, source, count):
        
        line = '****************************************\n'
        message = "Vocabs: " + str(vocabs).strip('[]').replace('\'','') + '\n'

        c = 0
        for k in vocab_dic.keys():
            all_def = vocab_dic[k][0]['definitions']
            all_ex = vocab_dic[k][0]['examples']
            all_sy = vocab_dic[k][0]['synonyms']
            message += line
            message += 'Vocab %d: ' % (c+1) + k + '\n'
            message += 'Source: ' + source[c] + '\n'
            message += line
            message += 'Definition: \n' 
            try:
                # Write Definitions
                for definition in range(len(all_def)):
                    message += '\t - ' + all_def[definition] + '\n'
                
                # Write Synonyms
                if all_sy != None:
                    message += '\nSynonyms: ' + all_sy[0][0]
                    for synonym in all_sy[1:]:
                        message += ', ' + synonym[0]
                    message += '\n'
                
                # Write Examples
                print(all_ex)
                if all_ex != []:
                    message += '\nExample: \n'
                    
                    for example in range(len(all_ex)):
                        message += '\t - ' +  all_ex[0][example].strip('\n ') + '\n'
                                    
            except:
                print('None')
                pass
            message += '\n\n'
            c += 1
        
        print(message)
        
        # slack access bot token
        slack_token = secret.slack_token("slack_token")
        
        data = {
            'token': slack_token,
            'channel': secret.slack_token("user_id"),    # User ID. 
            'as_user': True,
            'text': message
        }
        
        requests.post(url='https://slack.com/api/chat.postMessage',
                      data=data)

    def is_time_between(begin_time, end_time, check_time=None):
        # If check time is not given, default to current UTC time
        check_time = check_time or datetime.now().time()
        if begin_time < end_time:
            return check_time >= begin_time and check_time <= end_time
        else: # crosses midnight
            return check_time >= begin_time or check_time <= end_time
    
        
        
print("Retrieving Data...")
print()
Cnotion = Connect_Notion()
data = Cnotion.readDatabase(databaseId, headers)

# Notion only outputs 100 elements at a time so if it goes over, we need to 
# go to the next page in the database
data = Cnotion.next_page(data)

projects = Cnotion.get_projects_titles(data)
projects_data = Cnotion.get_projects_data(data, projects)
total_vocab_sug = Cnotion.adjust_suggestionRate(projects_data, total_vocab_sug)

new_vocab, source, count = Cnotion.execute_update(projects_data, headers)
vocab_dic = Cnotion.connect_LinguaAPI(new_vocab, secret.lingua_API('API Key'))
Cnotion.send_vocab(new_vocab, vocab_dic, source, count)




