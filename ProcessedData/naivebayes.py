import numpy as np
import pandas as pd
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn import linear_model
from sklearn.naive_bayes import GaussianNB

def get_features(columns):
    segmentation_annotation_labels = ['video', 'laughter_start', 'laughter_end', 'laughter_value',
       'start_segment_s', 'end_segment_s', 'start_segment_frame',
       'end_segment_frame','video_num']
    
    return sorted(list(set(list(columns)) - set(segmentation_annotation_labels)))

def late_fusion(audio_input_df,
                video_input_df,
                transcript_input_df,
                audio_features,
                video_features,
                transcript_features):
    #taking video num from audio data frame to divide video num for 5 experiments.     
    video_num_df = pd.DataFrame(list(audio_input_df.video_num.unique()))
    kf = KFold(n_splits=5)
    kf.get_n_splits(video_num_df)

    experiment = 0 
    for train_index, test_index in kf.split(video_num_df):
        print('Experiment : ', experiment)
        experiment = experiment + 1 

        #early fusion 

        df0 = audio_input_df
        df1 = video_input_df[video_features]#video_std_df[video_std_features]
        df2 = transcript_input_df[transcript_features]#transcript_input_df[transcript_features]
        early_fusion_frame = [df0,df1,df2]

        df0.index = df1.index 
        early_fusion_df = pd.concat(early_fusion_frame, axis=1)
        early_fusion_features = audio_features + video_features + transcript_features
        
        [early_fusion_prediction,early_fusion_accuracy] = get_prediction(early_fusion_df,
                                                                         early_fusion_features,
                                                                         train_index,
                                                                         test_index,
                                                                         experiment,
                                                                         'early_fusion')

        print("Early fusion : ",early_fusion_accuracy)
        
        #audio predition 
        
        [audio_prediction,audio_accuracy] = get_prediction(audio_input_df,
                                                           audio_features,
                                                           train_index,
                                                           test_index,
                                                           experiment,
                                                           'audio')
        
        print('Audio: ',audio_accuracy)
        
        #video prediction
        
        [video_predition, video_accuracy] = get_prediction(video_input_df,
                                                           video_features,
                                                           train_index,
                                                           test_index,
                                                           experiment,
                                                           'video')
        print('Video: ',video_accuracy)
        
        #transcript prediction
        
        [transcript_prediction,transcript_accuracy] = get_prediction(transcript_input_df,
                                                                     transcript_features,
                                                                     train_index,
                                                                     test_index,
                                                                     experiment,
                                                                     'transcript')
        print('Transcript: ',transcript_accuracy)
        
        
        
        late_fusion_list = []
        for i in range(len(audio_prediction)):
            late_fusion_list.append([
                    audio_prediction[i],
                    video_predition[i],
                    transcript_prediction[i]
                    ])
        
        accuracies = [audio_accuracy,video_accuracy,transcript_accuracy]
        
        max_accuracy = max(accuracies)
        max_index = accuracies.index(max_accuracy)
        
        late_fusion_result = []
        
        for segment_prediction in late_fusion_list:
            result = max_index
            if len(segment_prediction) != len(set(segment_prediction)):
                result = max(set(segment_prediction), key=segment_prediction.count)
            
            late_fusion_result.append(result)
        
        	
	#any other input data frame can be used. i've choosen audio_input_df. This is mainly to get laugther values. for test data.  
        test_data = []
        for video_num in test_index: 
            test_data.append(audio_input_df[audio_input_df.video_num == video_num])
        test_data = pd.concat(test_data)
        
        test_y = list(test_data.laughter_value)
        
        late_fusion_accuracy = accuracy_score(late_fusion_result,test_y) 
        
        print('late fusion accuracy : ', late_fusion_accuracy)
        
        
        print('+'*20)
        
def get_prediction(input_df,features,train_index,test_index,experiment,modality):
    
    train_data = []


    for video_num in train_index: 
        train_data.append(input_df[input_df.video_num == video_num])
    train_data2 = pd.concat(train_data)
    train_data3 = train_data2[features].values
    train_label3 = train_data2.laughter_value.values

    lengthTr=len(train_data3)

    train_data = []
    train_label = []
    validate_data = []
    validate_label = []

    #validation data
    i=0
    for i in range(0,((3*lengthTr)/4)):
        train_data.append(train_data3[i])
        train_label.append(train_label3[i])
    for i in range(((3*lengthTr)/4),lengthTr):
        validate_data.append(train_data3[i])
        validate_label.append(train_label3[i])

    test_data = []

    for video_num in test_index: 
        test_data.append(input_df[input_df.video_num == video_num])

    test_data = pd.concat(test_data)


    clf = GaussianNB()
    test_results=list()
    clf.fit(train_data, train_label)
    for line in validate_data:
        pred = clf.predict([line])[0]
        test_results.append(pred)
    accuracy = accuracy_score(validate_label, test_results)
    print "\n\nValidation accuracy= ",accuracy

    clf = GaussianNB()
    test_results=list()
    clf.fit(train_data, train_label)
    for line in test_data[features].values:
        pred = clf.predict([line])[0]
        test_results.append(pred)
    accuracy = accuracy_score(test_data.laughter_value.values,test_results)

    con_matrix = confusion_matrix(test_results, test_data.laughter_value.values)
    f1 = f1_score(test_results, test_data.laughter_value.values, average='macro')
    print "F1:  ",f1
    print con_matrix



    confPred = pd.DataFrame(clf.predict_proba(test_data[features].values))
    td_s = pd.Series(list(test_data.video_num),index=confPred.index)    
    #print('video_number : ', list(td_s))
    confPred["video_number"]=td_s
    confPred["prediction"] = test_results
    #confPred.columns = ['video_number','0','1','2','prediction']   
    #print td_s
    writer = pd.ExcelWriter("./conf_naiveBayes"+'_' +modality+ '_' + str(experiment) + ".xlsx")
    confPred.to_excel(writer,'Sheet1')
    writer.save()
    
    return [test_results,accuracy]       


def main():
	opensmile_std_input_df = pd.read_excel("Audio/open_face_accoustic_std.xlsx")
	opensmile_mean_input_df = pd.read_excel("Audio/open_face_accoustic_means.xlsx")
	transcript_input_df = pd.read_csv("Transcript/segment_annotation_transcript_features.csv")
	video_max_df = pd.read_csv("Video/feature_annotation_max.csv")
	video_min_df = pd.read_csv("Video/feature_annotation_min.csv")
	video_mean_df = pd.read_csv("Video/feature_annotation_mean.csv")
	video_std_df = pd.read_csv("Video/feature_annotation_sd.csv")

	num_dict = {}
	artists = list(transcript_input_df.video.unique())

	for artist_num in range(len(artists)):
	    num_dict[artists[artist_num]] = artist_num

	artist_num = []
	for artist in transcript_input_df.video:
	    artist_num.append(num_dict[artist])

	transcript_input_df['video_num'] = artist_num
	opensmile_std_input_df['video_num'] = artist_num
	opensmile_mean_input_df['video_num'] = artist_num
	transcript_input_df['video_num'] = artist_num
	video_max_df['video_num'] = artist_num
	video_min_df['video_num'] = artist_num
	video_mean_df['video_num'] = artist_num
	video_std_df['video_num'] = artist_num

	transcript_features = get_features(transcript_input_df.columns)
	opensmile_std_features = get_features(opensmile_std_input_df.columns)
	opensmile_mean_features = get_features(opensmile_mean_input_df.columns)
	video_max_features = get_features(video_max_df.columns)
	video_min_features = get_features(video_min_df.columns)
	video_mean_features = get_features(video_mean_df.columns)
	video_std_features = get_features(video_std_df.columns)


	late_fusion(opensmile_std_input_df,
           video_std_df,
           transcript_input_df,
           opensmile_std_features,
           video_std_features,
           transcript_features)

if __name__ == "__main__":
	main()
