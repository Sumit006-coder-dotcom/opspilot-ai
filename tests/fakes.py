import hashlib
import numpy as np
class FakeEmbeddings:
    def _vec(self,text):
        vector=np.zeros(32,dtype="float32")
        for word in text.lower().split():
            idx=int(hashlib.sha256(word.encode()).hexdigest()[:8],16)%32
            vector[idx]+=1
        norm=np.linalg.norm(vector)
        return (vector/(norm or 1)).tolist()
    def embed_documents(self,texts):return [self._vec(t) for t in texts]
    def embed_query(self,text):return self._vec(text)
