from transformers import AutoTokenizer, AutoModel
import torch


class Context_Vectorizer(object):
    def __init__(self, model_name=None) -> None:
        super().__init__()
        self.tokenizer = None
        self.model = None
        if model_name is None:
            self.model_name = 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
        else:
            self.model_name = model_name
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        self.cpu = "cpu"

    def load_model(self):
        if self.tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name)
        if self.model is None:
            self.model = AutoModel.from_pretrained(
                self.model_name)
            self.model = self.model.to(self.device)

    def vectorize(self, sentences):
        self.load_model()

        # Tokenize sentences
        encoded_input = self.tokenizer(sentences, padding=True,
                                       truncation=True, return_tensors='pt').to(self.device)

        # Compute token embeddings
        with torch.no_grad():
            model_output = self.model(**encoded_input)
        # Perform pooling. In this case, max pooling.
        sentence_embeddings = self.mean_pooling(
            model_output, encoded_input['attention_mask'])

        # return sentence_embeddings.to(self.cpu)
        return sentence_embeddings

    @staticmethod
    def mean_pooling(model_output, attention_mask):
        # First element of model_output contains all token embeddings
        token_embeddings = model_output[0]
        input_mask_expanded = attention_mask.unsqueeze(
            -1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
