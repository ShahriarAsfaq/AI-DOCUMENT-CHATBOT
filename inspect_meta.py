import pickle, pathlib
p=pathlib.Path('vectors/faiss_store/metadata.pkl')
with open(p,'rb') as f:
    data=pickle.load(f)
print('metadata_list length', len(data.get('metadata_list',[])))
print('document_metadata keys', list(data.get('document_metadata', {}).keys()))
print(data.get('document_metadata', {}))
