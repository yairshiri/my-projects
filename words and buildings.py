from random import randint

import pandas as pd
import tensorflow as tf
from tensorflow import keras
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import numpy as np
import matplotlib.pyplot as plt


def get_data1():
    dataset = pd.read_csv('new building.csv')
    dataset = dataset.sample(frac=1)
    words = dataset['word'][:3000]
    buildings = dataset['pattern'][:3000]
    return np.asarray(words, dtype=np.str), np.asarray(buildings, dtype=np.str)


def get_data():
    # redundant( already used, data cleaned)
    ret = []
    dataset = pd.read_csv('InflectedVerbsExtended.csv')
    words = dataset['vocalized_inflection']
    buildings = dataset['pattern_1']
    with open('InflectedVerbsExtended.txt', 'w', newline='', encoding="utf-8") as file:
        file.write('word,pattern\n')
        for i in zip(words, buildings):
            building = i[1]
            word = i[0]
            temp = ''
            for j, letter in enumerate(word):
                if letter in 'אבגדהוזחטיכלמנסעפצקרשתןםףךץ':
                    temp = temp.__add__(f'{letter} ')
            temp = temp[:-1]
            print(f"{temp}, {building}")
            file.write(f"{temp},{building}\n")
        file.close()

    return ret


words, buildings = get_data1()

encoder = LabelEncoder().fit(buildings)
classes = encoder.classes_
labels = encoder.transform(buildings)

labels = np.asarray(labels, dtype=np.int)

"""temp = []

for i,label in enumerate(labels):
    save = label
    temp.append([0,0,0,0,0,0,0,0,0,0])
    temp[i][save] = 1

labels = temp"""

tokenizer = keras.preprocessing.text.Tokenizer(oov_token='<oov>')
tokenizer.fit_on_texts(words)
train_features, test_features, train_labels, test_labels = train_test_split(words, labels, train_size=0.05)
padded_train_features = keras.preprocessing.sequence.pad_sequences(tokenizer.texts_to_sequences(train_features),
                                                                   padding='post').astype(np.int)
padded_test_features = keras.preprocessing.sequence.pad_sequences(tokenizer.texts_to_sequences(test_features),
                                                                  padding='post').astype(np.int)

vocab_size = len(tokenizer.word_index)

model = keras.models.Sequential(layers=[tf.keras.layers.Embedding(vocab_size + 1, 64),
                                        tf.keras.layers.Bidirectional(tf.keras.layers.LSTM(64,return_sequences=True,activity_regularizer=tf.keras.regularizers.l2())),
                                        tf.keras.layers.Dropout(0.5),
                                        tf.keras.layers.Bidirectional(tf.keras.layers.LSTM(64,activity_regularizer=tf.keras.regularizers.l2())),
                                        tf.keras.layers.BatchNormalization(),
                                        tf.keras.layers.Dense(32,activity_regularizer=tf.keras.regularizers.l2()),
                                        tf.keras.layers.Dropout(0.5),
                                        tf.keras.layers.Dense(32,activity_regularizer=tf.keras.regularizers.l2()),
                                        tf.keras.layers.Dense(len(labels), activation='softmax')])

model.compile(optimizer=keras.optimizers.RMSprop(), loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
              metrics=['accuracy'])

history = model.fit(padded_train_features, train_labels, validation_data=(padded_test_features, test_labels),
                    epochs=2000, batch_size=30)

plt.plot(history.history['accuracy'])
plt.plot(history.history['val_accuracy'])
plt.title('model accuracy')
plt.ylabel('accuracy')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
plt.show()
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('model loss')
plt.ylabel('loss')
plt.xlabel('epoch')
plt.legend(['train', 'test'], loc='upper left')
plt.show()


def predict_x(x):
    predictions = model.predict(padded_test_features[:x])
    ret = []
    global classes
    classes = list(set(classes))
    for i, prediction in enumerate(predictions):
        ret.append([classes[prediction.argmax()], classes[int(test_labels[i])]])
    return ret
