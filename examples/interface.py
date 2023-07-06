"""
"""
import os
import pickle
import textwrap

from typing import Dict, List

import tqdm
import torch
import numpy as np
import gradio as gr
import datasets as hfd
import langchain
import langchain.llms

import examples.simplesearch as ss
import neosophia.llmtools.util as util

from examples import project
from neosophia.llmtools import openaiapi as oaiapi

MAX_RULES = 5


def setup():
    """ Configuration and data loading """

    api_key = oaiapi.load_api_key(project.OPENAI_API_KEY_FILE_PATH).rstrip()
    oaiapi.set_api_key(api_key)

    with open('embeddings.pkl', 'rb') as f:
        records = pickle.load(f)

    rules = [
        {
            'name': str(x['rule_name']) + ' ' + str(x['section_label']),
            'text': x['text'],
            'emb': x['emb']
        } for x in records
    ]

    return records, rules


def _level(name: str) -> int:
    """find the level of the rule"""
    return len([x for x in name if x == '\'']) // 2


def main():

    records, _rules = setup()
    _rules = [
        rule for rule in _rules
        if _level(rule['name']) == 1
    ]

    rules = []
    for rule in _rules:
        rule_name = ' '.join(rule['name'].split()[:2])
        section_id = rule['name'].split()[2:][0]
        section_id = section_id.replace(
            '(', '').replace(')', '').replace(',', '').replace('\'', '')

        rules.append(
            {
                'name': rule_name + ' — ' + section_id,
                'text': rule['text'],
                'emb': rule['emb']
            }
        )

    def semantic_search(search_str):

        # get embedding of search string from OpenAI
        search_emb = oaiapi.extract_embeddings(
            oaiapi.embeddings([search_str]))[0]

        # perform a very simple vector search
        rule_idxs = ss.find_most_similar_idxs(rules, search_emb, MAX_RULES)

        # find the rule_text and create context
        rule_text = [
            rules[idx]['name'] + ': \n' + rules[idx]['text'] for idx in rule_idxs]
        context = '\n\n'.join(rule_text)

        rule_names = ', '.join([rules[idx]['name'] for idx in rule_idxs])

        rule_names = 'Relevant Rules: ' + rule_names

        return rule_names, context

    def format_search(search_str):
        rule_names, context = semantic_search(search_str)
        return 'Relevant Rules: ' + ''.join(rule_names) + '\n\n' + context

    def ask_question(question: str):
        # ask the question and get an answer
        _, context = semantic_search(question)
        answer = ss.qa_func(context=context, question=question)
        output = ['Answer: ' + answer + '\n\n']
        output.append(context)
        return ''.join(output)

    with gr.Blocks() as demo:
        gr.Markdown('# Semantic Search')
        with gr.Row():
            with gr.Column():
                question_input = gr.Textbox()
                question_button = gr.Button('Ask a question', scale=None)
        with gr.Row():
            with gr.Column():
                search_input = gr.Textbox()
                search_button = gr.Button('Search Rules', scale=None)

        gr.Markdown("# Results")
        with gr.Row():
            text_output = gr.Textbox()

        question_button.click(
            ask_question, inputs=question_input, outputs=text_output)

        search_button.click(
            format_search, inputs=search_input, outputs=text_output)

    demo.launch()


if __name__ == '__main__':
    main()

