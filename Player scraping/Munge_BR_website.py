import pandas as pd
import numpy as np

import re

from urllib.request import urlopen
from string import ascii_lowercase
from bs4 import BeautifulSoup, Comment

class scrape_BR(object):
    """docstring for scrape_BR."""
    def __init__(self, arg):
        super(scrape_BR, self).__init__()
        self.arg = arg

    def create_player_dataframe():
        '''
        method for creating all player's in BR player index,
        https://www.basketball-reference.com/players/a/_____ e.g.
        '''

        # make pandas dataframe for all player info
        player_df = pd.DataFrame(columns=["Player","BR_player_id","From","To",
                                          "Pos","Ht","Wt","Birth Date","College",
                                          "active","shoots","draft_team","pick_order",
                                          "draft_year_type"])

        j = 0
        for letter in ascii_lowercase:

            if letter == "x":
                continue

            url = "http://www.basketball-reference.com/players/"+str(letter)+"/"
            html = urlopen(url)
            soup = BeautifulSoup(html,'lxml')
            player_table = soup.select("#players")

            for i,row in enumerate(player_table[0].find_all("tr")):

                player_info = []

                # skip metadata
                if i == 0:
                    continue

                player_info.append(row.find_all("th")[0].text)
                BR_player_id = row.find_all("th")[0]['data-append-csv']
                player_info.append(BR_player_id)

                for row2 in row.find_all("td"):
                    player_info.append(row2.text)

                if "<strong>" in str(row.find_all("th")[0]):
                    player_info.append(int(1))
                else:
                    player_info.append(int(0))

                cols_to_fill = ["Player","BR_player_id","From","To",
                                "Pos","Ht","Wt","Birth Date","College",
                                "active"]

                player_df.loc[j,cols_to_fill] = player_info
                player_df = _get_player_meta_data(player_df,letter,BR_player_id)
                j+=1

        return player_df

    def _get_player_meta_data(df,letter,BR_player_id):
        temp_player_df = df.copy()
        player_index = temp_player_df[temp_player_df['BR_player_id'] == BR_player_id].index[0]

        url = "https://www.basketball-reference.com/players/"+str(BR_player_id)[0]+"/"+BR_player_id+".html"

        try:
            html = urlopen(url)
        except HTTPError:
            print(url)
            return temp_player_df

        soup = BeautifulSoup(html,'lxml')

        # find player info by div id
        meta_data = soup.find("div", {"id": "meta"})
        par_meta = meta_data.find_all('p')

        for val in par_meta:
            to_parse = val.text

            if "Shoots" in to_parse:
                shoots = "".join(to_parse.split('Shoots:')[1])
                shoots = shoots.strip()
                temp_player_df.loc[player_index,'shoots'] = shoots
            if "Position" in to_parse:
                position = "".join(to_parse.split('Position:')[1])
                position = position.strip().split("\n")[0]
                #temp_player_df.loc[player_index,''] = shoots
            if "Draft" in to_parse:
                draft_data = to_parse.split("Draft:")[1].split(',')
                team = draft_data[0].strip()
                temp_player_df.loc[player_index,'draft_team'] = team

                if len(draft_data) == 4:
                    pick_order = str(draft_data[1].strip())+","+str(draft_data[2].strip())
                    draft_year_type = draft_data[3].strip()
                    temp_player_df.loc[player_index,'pick_order'] = pick_order
                    temp_player_df.loc[player_index,'draft_year_type'] = draft_year_type
                elif len(draft_data) == 3:
                    pick_order = draft_data[1].strip()
                    draft_year_type = draft_data[2].strip()
                    temp_player_df.loc[player_index,'pick_order'] = pick_order
                    temp_player_df.loc[player_index,'draft_year_type'] = draft_year_type

        return temp_player_df

    def _get_the_soup(BR_player_id):
        url = "https://www.basketball-reference.com/players/"+BR_player_id[0]+"/"+BR_player_id+".html"
        html = urlopen(url)

        return BeautifulSoup(html,'lxml')

    def _get_player_div_tags(BR_player_id):
        soup = _get_the_soup(BR_player_id)
        div_tags = [entry.get("id") for entry in soup.find_all('div') if entry.get("id") is not None]

        possible_tags = []
        for tag in div_tags:
            if re.match('all',tag):
                if re.search(r"\d",tag):
                    continue
                if tag == "all_per_game":
                    continue
                possible_tags.append(tag)

        return possible_tags

    def create_player_df_per_game(BR_player_id):

        soup = _get_the_soup(BR_player_id)

        div_tag = "all_per_game"
        div_HTML = soup.find("div", {"id": div_tag})
        table_header = div_HTML.find('thead')
        table_body = div_HTML.find('tbody')
        col_headers = [info.getText().strip() for info in table_header.find_all('tr')]

        # returns a string for some reason, there must be a better way but this works
        col_headers = [val for val in col_headers[0].split()]
        df_all_per_game = pd.DataFrame(columns=col_headers)

        for i,row in enumerate(table_body.find_all('tr')):
            try:
                fill_vals = [row.find('th').text] + [val.text for val in row.find_all('td')]
            except AttributeError:
                fill_vals = [np.NaN]*len(col_headers)
            df_all_per_game.loc[i] = fill_vals

        return df_all_per_game

    def create_player_df_table(div_tag,BR_player_id):
        soup = _get_the_soup(BR_player_id)

        # parse via div_tags
        div_HTML = soup.find("div", {"id": div_tag})

        # sometimes data are in comments
        try:
            comments = div_HTML.findAll(text=lambda text:isinstance(text, Comment))
            div_soup = BeautifulSoup(comments[0],'lxml')
        except AttributeError:
            div_soup = div_HTML


        # to get table headers isolate thead
        table_header = div_soup.find('thead')

        table_body = div_soup.find('tbody')

        col_headers = [info.getText().strip() for info in table_header.find_all('tr')][0].split("\n")
        try:
            empty_header = [col_headers.index("")]
            for index in empty_header:
                del col_headers[index]
        except ValueError:
            empty_header = []

        df_all_totals = pd.DataFrame(columns=col_headers)
        for i,row in enumerate(table_body.find_all('tr')):
            try:
                fill_vals = [row.find('th').text] + [val.text for val in row.find_all('td')]
            except AttributeError:
                fill_vals = [np.NaN]*len(col_headers)
            
            if len(empty_header) > 0:
                for index in empty_header:
                    del fill_vals[index]

            df_all_totals.loc[i] = fill_vals

        return df_all_totals
