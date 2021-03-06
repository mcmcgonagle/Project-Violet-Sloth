from bs4 import BeautifulSoup
import requests
import boto3
from datetime import datetime, date

#Establish connection to Database
wotdDB = boto3.client('dynamodb')

#Lambda Handler function
def lambda_handler(event, context):
	languages = [{"language":"spanish", "link":"https://wotd.transparent.com/rss/es-widget.xml"},{"language":"chinese", "link":"https://wotd.transparent.com/rss/zh-widget.xml"}]
	#Scrap WOTD XML Feed for Today's words
	for item in languages:
		print(item)
		response  = requests.get(item["link"])
		data = response.text
		soup = BeautifulSoup(data, "xml")

		#Locate today's WOTD in database- must run query to find ID. Set result to wordID
		dbQuery =  wotdDB.query(
			TableName='wotd',
	        IndexName='language-word-index',
			ExpressionAttributeNames={"#L":"language"},
			ExpressionAttributeValues={":lang":{"S":item['language']},":word":{"S":soup.word.get_text()}},
			KeyConditionExpression="#L = :lang AND word = :word"
	    )
		wordID = dbQuery['Items'][0]['id']['N']

		#Set today's Word of the Day to active
		dbUpdater = wotdDB.update_item(
			ExpressionAttributeNames={
				'#IA': 'isActive'
			},
			ExpressionAttributeValues={
				':ia':{
				'BOOL': True,
				},
				':LA':{
				'S': date.strftime(datetime.utcnow(),"%Y-%m-%d"),
				},
			},
			TableName='wotd',
			ReturnValues='ALL_NEW',
			Key={
				"language": {
					"S": item['language']
				},
				"id":{
					"N": wordID
				},
			},
			UpdateExpression='SET #IA=:ia, lastActive=:LA'
		)
		print(dbUpdater)

		#Find any other active WOTD items that are not today's word
		dbFindActive =  wotdDB.query(
			TableName='wotd',
			ExpressionAttributeNames={"#L":"language"},
			ExpressionAttributeValues={":lang":{"S":item['language']},":idVal":{"N":"0"},":isActiveVal":{"BOOL":True},":word":{"S":soup.word.get_text()}},
			KeyConditionExpression="#L = :lang AND id > :idVal",
			FilterExpression="isActive = :isActiveVal AND word <> :word"
	    )

		#Loop through items that are not supposed to be active and set to inactive
		for item in dbFindActive['Items']:
			dbSetInactive = wotdDB.update_item(
				ExpressionAttributeNames={
					'#IA': 'isActive',
				},
				ExpressionAttributeValues={
					':ia':{
					'BOOL': False,
					},
				},
				TableName='wotd',
				Key={
					"language": {
						"S": item['language']["S"]
					},
					"id":{
						"N": item['id']["N"]
					},
				},
				UpdateExpression='SET #IA=:ia'
			)
			print(dbSetInactive)
		

	return "WOTD has been updated."
