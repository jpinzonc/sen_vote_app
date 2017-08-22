from   flask  import Flask, render_template, g, request, url_for
import pandas as pd
from   pandas import read_sql_query as rsq
import sqlite3
import folium
from   folium import IFrame

def vote_count_all(df_votes): # Detemines total number of votes for each category (Yea, Nai, Not Voting, Present) per Senator and per Party
    # Can be divided into vote_count_senator(df) and vote_count_party(df)
    unique_votes=list(df_votes.iloc[:,8:len(df_votes.columns)].stack().unique()) # Unique votes categories in df
    # VOTES PER SENATOR (vote_count_senator(df))
    # Add non-vote columns to index
    l_index=list(df_votes.iloc[:,0:8]) 
    df1 = df_votes.set_index(l_index)
    df  = df_votes.set_index(l_index)
    # Counting votes per senator
    for vote in range(0,len(unique_votes)):
        df1[unique_votes[vote]] = df[df==unique_votes[vote]].count(axis=1)
    df1_total = pd.DataFrame(df1.sum(1), columns=['Total'])
    # Calculate percent of vote for each senator
    df1 = df1[unique_votes]
    df_sen = round(df1.div(df1.sum(1)/100,0),2)
    df_sen = df_sen.merge(df1_total, right_index=True, left_index=True)
    #Re-ser the index
    df_sen = df_sen.reset_index(l_index)
    #return df_sen
    # VOTES PER PARTY (vote_count_party(df))
    # Remove columns with information on the senators
    df3  = df_votes.drop(["Year", 'Congress', 'Session', 'Member','First','Last','State'], axis=1)
    # Add non-vote columns to index
    l_index_par = list(df3.iloc[:,0:1])
    df4  = df3.set_index(l_index_par)
    df3  = df3.set_index(l_index_par)
    # Counting votes per party
    for vote in range(0,len(unique_votes)):
        df4[unique_votes[vote]] = df3[df3==unique_votes[vote]].count(axis=1)
    df4 = df4[unique_votes]
    df4 = df4.groupby(df4.index)[unique_votes].sum()
    df4_total=pd.DataFrame(df4.sum(1), columns=['Total'])
    # Calculate percent of vote for each part
    df_par = round(df4.div(df4.sum(1)/100,0),2)
    df_par = df_par.merge(df4_total, right_index=True, left_index=True)
    # Re-set the index
    df_par = df_par.reset_index()
    #return df_par
    # Returs both df
    #return (df_sen, df_par) # as tuple
    return pd.Series({'Senator_total': df_sen, 'Party_total': df_par}) # as Series

def get_cong_ses_db(year): # Necessary to complete the table name in the db_votes function
    conn = sqlite3.connect('files/sen_vote.db')
    cong = int(rsq(("SELECT * FROM congres_tb WHERE year ="+str(year)+""), conn)['congress'])
    sess = int(rsq(("SELECT * FROM congres_tb WHERE year ="+str(year)+""), conn)['session'])
    return pd.Series({'Congress': cong, 'Session': sess}) 

def db_votes(year): # Runs the vote_count_all function on the appropriate df after a sql query
    conn = sqlite3.connect('files/sen_vote.db')
    tablename = str("vote_"+str(year)+"_"+str(get_cong_ses_db(year)[0])+"_"+str(get_cong_ses_db(year)[1]))
    que=("SELECT * FROM "+ tablename +" ;")
    dbvot = vote_count_all(rsq(que,conn))
    return dbvot

def map_create(df_sen, latlon):
    #latlon= pd.read_csv('files/us_lat_lon.csv')
    width, height = 1250, 450
    # CREATE MAP:
    sen_map = folium.Map(location=[40, -115], zoom_start=3, tiles='Stamen Terrain',
                         width=width, height=height)
    # CLUSTER POINTS
    marker_cluster = folium.MarkerCluster().add_to(sen_map)
    #inline_map(radars)
    for row in range(0,len(latlon)):
        state_name = latlon['state_name'][row]
        state      = latlon['state'][row]
        lon        = latlon['lon'][row]
        lat        = latlon['lat'][row]
        df         = df_sen.loc[df_sen['State'] == state]
        for row in df.index:
            if   df['Party'][row] == 'R':
                color = "red"
            elif df['Party'][row] == 'D':
                color = "blue"
            elif df['Party'][row] == 'I':
                color = 'green'
            else:
                color = 'black'
            html="""
            <h1>{}</h1><br>
            <table style="width:100%">
            <tr, td aling="center">
            <th>First</th>
            <th>Last</th> 
            <th>Party</th>
            <th>Yeas</th>
            <th>Nay</th>
            <th>No vote</th>
            <th>Total</th>
            </tr>
            <tr>
            <td align="center">{}</td>
            <td align="center">{}</td> 
            <td align="center">{}</td>
            <td align="center">{}</td>
            <td align="center">{}</td>
            <td align="center">{}</td>
            <td align="center">{}</td>
            </tr>
            </table>
            """
            html = html.format(state_name,df['First'][row],df['Last'][row],df['Party'][row],
            		 df['Yea'][row], df['Nay'][row], df['Not Voting'][row],df['Total'][row])
            iframe = IFrame(html=html, width=400, height=200)
            popup  = folium.Popup(iframe, max_width=2650)
            icon   = folium.Icon(color=color ,icon='circle')
            folium.Marker((lat,lon), popup=popup,icon = icon,).add_to(marker_cluster)
    return sen_map

app = Flask(__name__)

@app.route('/', methods = ['POST', 'GET'])
def index():
	latlon  = pd.read_csv('files/us_lat_lon.csv')
	if request.method == 'POST':
		year = request.form['year']
	else:
		year = 2017
	v_o_t_e = db_votes(year)
	Sen_db  = v_o_t_e[1]
	sen_map = Sen_db.drop(['Year','Congress','Session'], axis=1)
	sen_map = map_create(sen_map, latlon)
	sen_map.save('templates/map.html')
	return render_template('index.html', year = year)


if __name__ == '__main__':
    app.run(debug=True)
