import theano
from theano import tensor as T
import numpy as np

def floatX(X):
    return np.asarray(X, dtype=theano.config.floatX)

def init_weights(shape):
    return theano.shared(floatX(np.random.randn(*shape) * 0.01))

def init_tanh(n_in, n_out):
    rng = np.random.RandomState(1234)
    return theano.shared(np.asarray(
                rng.uniform(
                    low=-np.sqrt(6. / (n_in + n_out)),
                    high=np.sqrt(6. / (n_in + n_out)),
                    size=(n_in, n_out)
                ),
                dtype=theano.config.floatX
            ))

def sgd(cost, params, lr=0.05):
    grads = T.grad(cost=cost, wrt=params)
    updates = []
    for p, g in zip(params, grads):
        updates.append([p, p + (-g * lr)])
    return updates

class NeuralNet(object):
    
    def __init__(self, input, n_in, n_out):

        hidden_size=36
        self._w_h = init_tanh(n_in, hidden_size)
        self._b_h = theano.shared(np.zeros((hidden_size,), dtype=theano.config.floatX) + 0.1)
        self._w_o = init_weights((hidden_size, n_out))
        self._b_o = theano.shared(np.zeros((n_out,), dtype=theano.config.floatX) + 0.1)
        
        self.updateTargetModel()
        """
        self._w_h_old = init_tanh(n_in, hidden_size)
        self._b_h_old = theano.shared(np.zeros((hidden_size,), dtype=theano.config.floatX))
        self._w_o_old = theano.shared(np.zeros(
                (hidden_size, n_out),
                dtype=theano.config.floatX
            ))
        self._b_o_old = theano.shared(np.zeros((n_out,), dtype=theano.config.floatX))
        """
        # print "Initial W " + str(self._w_o.get_value()) 
        
        self._learning_rate = 0.001
        self._discount_factor= 0.8
        
        self._weight_update_steps=5000
        self._updates=0
        
        
        State = T.fmatrix()
        ResultState = T.fmatrix()
        Reward = T.fmatrix()
        # Q_val = T.fmatrix()
        
        # model = T.nnet.sigmoid(T.dot(State, self._w) + self._b.reshape((1, -1)))
        # self._model = theano.function(inputs=[State], outputs=model, allow_input_downcast=True)
        py_x = self.model(State, self._w_h, self._b_h, self._w_o, self._b_o)
        y_pred = T.argmax(py_x, axis=1)
        q_val = py_x
        
        # cost = T.mean(T.nnet.categorical_crossentropy(py_x, Y))
        # delta = ((Reward.reshape((-1, 1)) + (self._discount_factor * T.max(self.model(ResultState), axis=1, keepdims=True)) ) - self.model(State))
        delta = ((Reward + (self._discount_factor * 
                            T.max(self.model(ResultState, self._w_h_old, self._b_h_old, self._w_o_old, self._b_o_old), axis=1, keepdims=True)) ) - 
                            T.max(self.model(State, self._w_h, self._b_h, self._w_o, self._b_o), axis=1,  keepdims=True))
        bellman_cost = T.mean( 0.5 * ((delta) ** 2 ))
        # bellman_cost = T.mean( 0.5 * ((delta) ** 2 )) + (T.sum(self._w_h**2) + T.sum(self._b_h ** 2) + 
          #                                              T.sum(self._w_o**2) + T.sum(self._b_o ** 2))

        params = [self._w_h, self._b_h, self._w_o, self._b_o]
        updates = sgd(bellman_cost, params, lr=self._learning_rate)
        
        self._train = theano.function(inputs=[State, Reward, ResultState], outputs=bellman_cost, updates=updates, allow_input_downcast=True)
        self._predict = theano.function(inputs=[State], outputs=y_pred, allow_input_downcast=True)
        self._q_values = theano.function(inputs=[State], outputs=py_x, allow_input_downcast=True)
        self._bellman_error = theano.function(inputs=[State, Reward, ResultState], outputs=delta, allow_input_downcast=True)
        
        
    def model(self, State, w_h, b_h, w_o, b_o):
        h = T.tanh(T.dot(State, w_h) + b_h)
        qyx = T.tanh(T.dot(h, w_o) + b_o)
        return qyx
    
    def updateTargetModel(self):
        print "Updating target Model"
        self._w_h_old = self._w_h 
        self._b_h_old = self._b_h 
        self._w_o_old = self._w_o 
        self._b_o_old = self._b_o 
    
    def train(self, state, reward, result_state):
        if (( self._updates % self._weight_update_steps) == 0):
            self.updateTargetModel()
        self._updates += 1
        return self._train(state, reward, result_state)
    
    def predict(self, state):
        return self._predict(state)
    def q_values(self, state):
        return self._q_values(state)
    def q_value(self, state):
        return np.max(self.q_values(state))
    def bellman_error(self, state, reward, result_state):
        return self._bellman_error(state, reward, result_state)
