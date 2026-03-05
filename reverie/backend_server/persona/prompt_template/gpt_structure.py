"""
Author: Joon Sung Park (joonspk@stanford.edu)
Modified to use vLLM server + local sentence-transformers for embeddings.
"""
import json
import time
from openai import OpenAI
from sentence_transformers import SentenceTransformer

from utils import *

# vLLM client
client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

# Local embedding model (downloads ~90MB on first run)
_embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

MODEL = "meta-llama/Llama-3.3-70B-Instruct"


def temp_sleep(seconds=0.1):
    time.sleep(seconds)


def ChatGPT_single_request(prompt):
    temp_sleep()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": "You are a helpful assistant. Always respond in plain text only. Never use markdown formatting, headers, bold text, bullet points, or any special formatting. Follow the exact output format specified in the user's prompt."},
                {"role": "user", "content": prompt}]
    )
    return completion.choices[0].message.content


# ============================================================================
# #####################[SECTION 1: CHATGPT-3 STRUCTURE] ######################
# ============================================================================

def GPT4_request(prompt):
    temp_sleep()
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON only. No markdown, no code fences, no extra text outside the JSON object."},
                {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content
    except:
        print("ChatGPT ERROR")
        return "ChatGPT ERROR"


def ChatGPT_request(prompt):
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "You are a helpful assistant. Always respond with valid JSON only. No markdown, no code fences, no extra text outside the JSON object."},
                {"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return completion.choices[0].message.content
    except:
        print("ChatGPT ERROR")
        return "ChatGPT ERROR"


def GPT4_safe_generate_response(prompt,
                                example_output,
                                special_instruction,
                                repeat=3,
                                fail_safe_response="error",
                                func_validate=None,
                                func_clean_up=None,
                                verbose=False):
    prompt = 'GPT-3 Prompt:\n"""\n' + prompt + '\n"""\n'
    prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
    prompt += "Example output json:\n"
    prompt += '{"output": "' + str(example_output) + '"}'

    if verbose:
        print("CHAT GPT PROMPT")
        print(prompt)

    for i in range(repeat):
        try:
            curr_gpt_response = GPT4_request(prompt).strip()
            end_index = curr_gpt_response.rfind('}') + 1
            curr_gpt_response = curr_gpt_response[:end_index]
            curr_gpt_response = json.loads(curr_gpt_response)["output"]

            if func_validate(curr_gpt_response, prompt=prompt):
                return func_clean_up(curr_gpt_response, prompt=prompt)

            if verbose:
                print("---- repeat count: \n", i, curr_gpt_response)
                print("~~~~")
        except:
            pass

    return False


def ChatGPT_safe_generate_response(prompt,
                                   example_output,
                                   special_instruction,
                                   repeat=3,
                                   fail_safe_response="error",
                                   func_validate=None,
                                   func_clean_up=None,
                                   verbose=False):
    prompt = '"""\n' + prompt + '\n"""\n'
    prompt += f"Output the response to the prompt above in json. {special_instruction}\n"
    prompt += "Example output json:\n"
    prompt += '{"output": "' + str(example_output) + '"}'

    if verbose:
        print("CHAT GPT PROMPT")
        print(prompt)

    for i in range(repeat):
        try:
            curr_gpt_response = ChatGPT_request(prompt).strip()
            # strip markdown code fences Qwen sometimes adds
            curr_gpt_response = curr_gpt_response.replace("```json", "").replace("```", "").strip()
            end_index = curr_gpt_response.rfind('}') + 1
            curr_gpt_response = curr_gpt_response[:end_index]
            curr_gpt_response = json.loads(curr_gpt_response)["output"]

            if func_validate(curr_gpt_response, prompt=prompt):
                return func_clean_up(curr_gpt_response, prompt=prompt)

            if verbose:
                print("---- repeat count: \n", i, curr_gpt_response)
                print("~~~~")
        except Exception as e:
            if verbose:
                print(f"---- repeat count: {i}, error: {e}")

    return False


def ChatGPT_safe_generate_response_OLD(prompt,
                                       repeat=3,
                                       fail_safe_response="error",
                                       func_validate=None,
                                       func_clean_up=None,
                                       verbose=False):
    if verbose:
        print("CHAT GPT PROMPT")
        print(prompt)

    for i in range(repeat):
        try:
            curr_gpt_response = ChatGPT_request(prompt).strip()
            if func_validate(curr_gpt_response, prompt=prompt):
                return func_clean_up(curr_gpt_response, prompt=prompt)
            if verbose:
                print(f"---- repeat count: {i}")
                print(curr_gpt_response)
                print("~~~~")
        except:
            pass

    print("FAIL SAFE TRIGGERED")
    return fail_safe_response


# ============================================================================
# ###################[SECTION 2: ORIGINAL GPT-3 STRUCTURE] ###################
# ============================================================================

def GPT_request(prompt, gpt_parameter):
    """
    Previously used openai.Completion (legacy). Now routed through
    chat completions since vLLM serves chat models.
    """
    temp_sleep()
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a text completion engine. The user provides text that ends "
                    "mid-sequence. Continue ONLY from where the text ends, following the "
                    "exact same format as the examples shown. Output ONLY the continuation. "
                    "Do not add any preamble, explanation, title, or extra text. "
                    "Do not repeat what was already written."
                )},
                {"role": "user", "content": prompt},
            ],
            temperature=gpt_parameter["temperature"],
            max_tokens=gpt_parameter["max_tokens"],
            top_p=gpt_parameter["top_p"],
            frequency_penalty=gpt_parameter["frequency_penalty"],
            presence_penalty=gpt_parameter["presence_penalty"],
            stop=gpt_parameter["stop"],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print("TOKEN LIMIT EXCEEDED")
        print(f"GPT_REQUEST ERROR: {e}")
        return "TOKEN LIMIT EXCEEDED"


def generate_prompt(curr_input, prompt_lib_file):
    if type(curr_input) == type("string"):
        curr_input = [curr_input]
    curr_input = [str(i) for i in curr_input]

    f = open(prompt_lib_file, "r")
    prompt = f.read()
    f.close()
    for count, i in enumerate(curr_input):
        prompt = prompt.replace(f"!<INPUT {count}>!", i)
    if "<commentblockmarker>###</commentblockmarker>" in prompt:
        prompt = prompt.split("<commentblockmarker>###</commentblockmarker>")[1]
    return prompt.strip()


def safe_generate_response(prompt,
                           gpt_parameter,
                           repeat=5,
                           fail_safe_response="error",
                           func_validate=None,
                           func_clean_up=None,
                           verbose=False):
    if verbose:
        print(prompt)

    for i in range(repeat):
        curr_gpt_response = GPT_request(prompt, gpt_parameter)
        if func_validate(curr_gpt_response, prompt=prompt):
            return func_clean_up(curr_gpt_response, prompt=prompt)
        if verbose:
            print("---- repeat count: ", i, curr_gpt_response)
            print("~~~~")
    return fail_safe_response


def get_embedding(text, model=None):
    """
    Uses local sentence-transformers instead of OpenAI's embedding API.
    The model parameter is kept for compatibility but ignored.
    """
    text = text.replace("\n", " ")
    if not text:
        text = "this is blank"
    return _embedding_model.encode(text).tolist()


if __name__ == '__main__':
    gpt_parameter = {"engine": MODEL, "max_tokens": 50,
                     "temperature": 0, "top_p": 1, "stream": False,
                     "frequency_penalty": 0, "presence_penalty": 0,
                     "stop": ['"']}
    curr_input = ["driving to a friend's house"]
    prompt_lib_file = "prompt_template/test_prompt_July5.txt"
    prompt = generate_prompt(curr_input, prompt_lib_file)

    def __func_validate(gpt_response, prompt=None):
        if len(gpt_response.strip()) <= 1:
            return False
        if len(gpt_response.strip().split(" ")) > 1:
            return False
        return True

    def __func_clean_up(gpt_response, prompt=None):
        return gpt_response.strip()

    output = safe_generate_response(prompt,
                                    gpt_parameter,
                                    5,
                                    "rest",
                                    __func_validate,
                                    __func_clean_up,
                                    True)
    print(output)