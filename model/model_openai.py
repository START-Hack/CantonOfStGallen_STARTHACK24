from openai import OpenAI
import numpy as np
import pandas as pd
import os
import faiss
from bs4 import BeautifulSoup
import requests

class LanguageModelYosef:
    def __init__(self, api_key):
        self.client = OpenAI(api_key)
        self.system_prompt = """You are a voice bot working for the government of Canton St Gallen who responds to calls all around Switzerland. Please answer the call in the language of the caller. You will respond only based on the given retrieved information below. If there are no retrieved information, then you will say we are going to redirect you to the general hotline at +41712245121.
        # Retrieved Information: 
        {context}
        """ 
        self.df = pd.read_excel("./st-gallen-data.xlsx", sheet_name='data')
        self.index = self._get_index()
        self.keys = self._get_keys()
        

    def _get_index(self):
        index_file_path = "./keys.index"
        index = faiss.read_index(index_file_path)
        return index

    def _get_keys(self):
        
        self.df["keys"] = self.df["path_to_data_files"].map(lambda x: os.path.basename(x).replace("-", " ")).to_list() 
        keys = self.df["keys"].to_list()

        return keys

    def _get_embedding(self, q):
        embeddings = self.client.embeddings.create(
        model="text-embedding-ada-002",
        input=q,
        encoding_format="float"
        )
        result = [e.embedding for e in embeddings.data]
        return result


    def _get_urls(self, q, k):
        query = np.array(self._get_embedding(q)).astype("float32") 
        D, I = self.index.search(query,k)
        indices = I[0][:]
        urls = self.df["source"].to_list()
        return [urls[i] for i in indices]


    def _scrape_texts(self, urls):
        sections = []
        for url in urls:
            texts = []
            response = requests.get(url)
            soup = BeautifulSoup(response.content, "html.parser")   
            nodes = soup.select("div.portalsg-p-container")
        
            for node in nodes:
                for child in node.select("p, ul.rte > li"):
                    if child.name == "li":   
                        texts += [f"- {child.get_text()}"]
                    else:
                        texts += [child.get_text()]
            if texts:
                sections += ["# Source:\n" + url + "\n# Content:\n" + '\n'.join(texts)]
        return "\n\n".join(sections)
    
    def _get_context(self, query, k):
        return self._scrape_texts(self._get_urls(query, k))

    def get_response(self, query, k):
        final_system_prompt = self.system_prompt.replace("{context}", self._get_context(query, k))
        completion = self.client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=[
            {"role": "system", "content": final_system_prompt},
            {"role": "user", "content": query}
            ]
        )
        print(query)
        print(final_system_prompt)
        return completion.choices[0].message.content
