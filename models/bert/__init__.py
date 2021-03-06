from typing import List, Dict, Tuple, Any, Optional
import numpy as np

from models import Embedding, TF_SESS
import tensorflow as tf
import tensorflow_hub as hub
from tqdm import tqdm
from bert.tokenization import FullTokenizer


class Embeddings(object):

    EMBEDDING_MODELS: List[Embedding] = [
                        Embedding(name=u'bert_base_uncased',
                                  dimensions=768,
                                  corpus_size='3300M',
                                  vocabulary_size='30522(sub-word)',
                                  download_url='https://storage.googleapis.com/tfhub-modules/'
                                               'google/bert_uncased_L-12_H-768_A-12/1.tar.gz',
                                  format='tar.gz',
                                  architecture='Transformer, Layers=12, Hidden = 768, heads = 12',
                                  trained_data='BooksCorpus(800M) English Wikipedia (2500M) words',
                                  language='en'),

                        Embedding(name=u'bert_base_cased',
                                  dimensions=768,
                                  corpus_size='3300M',
                                  vocabulary_size='30522(sub-word)',
                                  download_url='https://storage.googleapis.com/tfhub-modules/google/'
                                               'bert_cased_L-12_H-768_A-12/1.tar.gz',
                                  format='tar.gz',
                                  architecture='Transformer Layers=12, Hidden = 768, heads = 12',
                                  trained_data='BooksCorpus(800M) English Wikipedia (2500M) words',
                                  language='en'),

                        Embedding(name=u'bert_multi_cased',
                                  dimensions=768,
                                  corpus_size='3300M',
                                  vocabulary_size='30522 (sub-word)',
                                  download_url='https://storage.googleapis.com/tfhub-modules/google/'
                                               'bert_multi_cased_L-12_H-768_A-12/1.tar.gz',
                                  format='tar.gz',
                                  architecture='Transformer Layers=12, Hidden = 768, heads = 12',
                                  trained_data='BooksCorpus(800M) English Wikipedia (2500M) words',
                                  language='en'),

                        Embedding(name=u'bert_large_uncased',
                                  dimensions=1024,
                                  corpus_size='3300M',
                                  vocabulary_size='30522 (sub-word)',
                                  download_url='https://storage.googleapis.com/tfhub-modules/google/'
                                               'bert_uncased_L-24_H-1024_A-16/1.tar.gz',
                                  format='tar.gz',
                                  architecture='Transformer Layers=24, Hidden = 1024, heads = 16',
                                  trained_data='BooksCorpus(800M) English Wikipedia (2500M) words',
                                  language='en'),

                        Embedding(name=u'bert_large_uncased',
                                  dimensions=1024,
                                  corpus_size='3300M',
                                  vocabulary_size='30522 (sub-word)',
                                  download_url='https://storage.googleapis.com/tfhub-modules/google/'
                                               'bert_uncased_L-24_H-1024_A-16/1.tar.gz',
                                  format='tar.gz',
                                  architecture='Transformer Layers=24, Hidden = 1024, heads = 16',
                                  trained_data='BooksCorpus(800M) English Wikipedia (2500M) words',
                                  language='en')
                        ]

    EMBEDDING_MODELS: Dict[str, Embedding] = {embedding.name: embedding for embedding in EMBEDDING_MODELS}

    tokenizer: FullTokenizer = None

    def __init__(self):
        self.sess = tf.Session()
        self.bert_module = None
        self.model = None

    def create_tokenizer_from_hub_module(self, model_path: str):
        """Get the vocab file and casing info from the Hub module."""
        tokenization_info = self.bert_module(signature="tokenization_info", as_dict=True)
        vocab_file, do_lower_case = self.sess.run(
            [
                tokenization_info["vocab_file"],
                tokenization_info["do_lower_case"],
            ]
        )

        Embeddings.tokenizer = FullTokenizer(vocab_file=vocab_file, do_lower_case=do_lower_case)

    @staticmethod
    def _model_single_input(text: str, max_seq_length: int) -> Tuple[List[int], List[int], List[int]]:
        tokens_a = Embeddings.tokenizer.tokenize(text)
        if len(tokens_a) > max_seq_length - 2:
            tokens_a = tokens_a[0: (max_seq_length - 2)]

        tokens = []
        segment_ids = []
        tokens.append("[CLS]")
        segment_ids.append(0)
        for token in tokens_a:
            tokens.append(token)
            segment_ids.append(0)
        tokens.append("[SEP]")
        segment_ids.append(0)

        input_ids = Embeddings.tokenizer.convert_tokens_to_ids(tokens)

        # The mask has 1 for real tokens and 0 for padding tokens. Only real
        # tokens are attended to.
        input_mask = [1] * len(input_ids)

        # Zero-pad up to the sequence length.
        while len(input_ids) < max_seq_length:
            input_ids.append(0)
            input_mask.append(0)
            segment_ids.append(0)

        assert len(input_ids) == max_seq_length
        assert len(input_mask) == max_seq_length
        assert len(segment_ids) == max_seq_length

        return input_ids, input_mask, segment_ids

    def load_model(self, model: str, model_path: str):
        self.bert_module = hub.Module(model_path)
        self.create_tokenizer_from_hub_module(model_path)
        self.model = model
        print("Model loaded Successfully !")

    def encode(self, texts: list, pooling: str = 'mean', **kwargs) -> Optional[np.array]:
        max_seq_length = kwargs.get('max_seq_length', 128)
        input_ids, input_masks, segment_ids = [], [], []
        for text in tqdm(texts, desc="Converting texts to features"):
            input_id, input_mask, segment_id = self._model_single_input(text, max_seq_length)
            input_ids.append(input_id)
            input_masks.append(input_mask)
            segment_ids.append(segment_id)

        bert_inputs = dict(
            input_ids=np.array(input_ids),
            input_mask=np.array(input_masks),
            segment_ids=np.array(segment_ids))

        bert_outputs = self.bert_module(bert_inputs, signature="tokens", as_dict=True)
        sequence_output = bert_outputs["sequence_output"]

        if not pooling:
            return sequence_output

        if pooling == 'mean':
            return tf.reduce_mean(sequence_output, 0)

        elif pooling == 'max':
            return tf.reduce_max(sequence_output, 0)

        elif pooling == 'min':
            return tf.reduce_min(sequence_output, 0)

        elif pooling == 'mean_max':
            return tf.concat(values=[tf.reduce_mean(sequence_output, 0), tf.reduce_max(sequence_output, 0)], axis=0)
        else:
            print(f"Pooling method \"{pooling}\" not implemented")
        return None
