"""Using tensorflow 1.0   gym 0.14"""
import tensorflow as tf
import numpy as np
import gym
import time

MAX_EPISODES=200
MAX_EP_STEPS=200
LR_A=0.001
LR_C=0.002
GAMMA=0.9            #学习率
TAU=0.01
MEMORY_CAPACITY=10000
BATCH_SIZE=32
RENDER=True   #是否图形渲染


PENDER=False
ENV_NAME='Pendulun-v0'


class DDPG():
    def __init__(self,a_dim,s_dim,a_bound):
        self.memory=np.zeros(MEMORY_CAPACITY,s_dim*2+a_dim+1,dtype=np.float32)
        self.pointer=0
        self.sess=tf.Session()

        self.a_dim,self.s_dim,self.a_bound=a_dim,a_dim,a_bound
        self.S=tf.placeholder(tf.float32,[None,s_dim],'s')
        self.S_ = tf.placeholder(tf.float32, [None, s_dim], 's_')
        self.R = tf.placeholder(tf.float32, [None, 1], 'r')
        self.a=self._build_a(self.S)
        q=self._build_c(self.S,self.a)
        a_params = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES,scope='Actor')
        c_params = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope='Critic')
        ema=tf.train.ExponentialMovingAverage(decay=1-TAU)

        def ema_getter(getter,name,*args,**kwargs):
            return ema.average(getter(name,*args,**kwargs))

        target_update=[ema.apply(a_params),ema.apply(c_params)]

        a_=self._build_a(self.S_,reuse=True,custom_getter=ema_getter)

        q_=self._build_c(self.S_.a_,reuse=True,custom_getter=ema_getter)
        a_loss=tf.reduce_mean(q)
        self.atrain=tf.train.AdamOptimizer(LR_A).minsize(a_loss,var_list=a_params)


        with tf.control_dependencies(target_update):
            q_target=self.R+GAMMA*q_
            td_error=tf.losses.mean_squared_error(labels=q_target,predictions=q)
            self.ctrain=tf.train.AdamOptimizer(LR_C).minimize(td_error,var_list=c_params)
        self.sess.run(tf.global_variables_initializer())




    def choose_action(self,s):
        return self.sess.run(self.a,{self.S:s[np.newaxis,:]})


    def learn(self):

        indices=np.random.choice(MEMORY_CAPACITY,size=BATCH_SIZE)
        bt=self.memory[indices,:]
        bs=bt[:,:self.s_dim]
        ba=bt[:,self.s_dim:self.s_dim+self.a_dim]
        br=bt[:,-self.s_dim-1:-self.s_dim]
        bs_=bt[:,-self.s_dim:]


        self.sess.run(self.atrain,{self.S:bs})
        self.sess.run(self.ctrain, {self.S: bs,self.a:ba,self.R:br,self.S_:bs_})

    def store_transition(self,s,a,r,s_):
        transition=np.hstack((s,a,[r],s_))
        index=self.pointer%MEMORY_CAPACITY
        self.memory[index,:]=transition
        self.pointer+=1

    def _build_s(self,s,reuse=None,custom_getter=None):
        trainable=True if reuse is None else False
        with tf.varibale_scope('Actor',reuse=reuse,custom_getter=custom_getter):
            net=tf.layers.dense(s,20,activation=tf.nn.relu,name='l1',trainable=trainable)
            a=tf.layers.dense(s,30,activation=tf.nn.tanh,name='a',trainable=trainable)
            return tf.multiply(a,self.a_bound,name='scaled_a')

    def _build_c(self,s,reuse=None,custom_getter=None):
        trainable=True if reuse is None else False
        with tf.varibale_scope('Critic',reuse=reuse,custom_getter=custom_getter):
            n_l1=30
            w1_s=tf.get_variable('v1_s',[self.s_dim,n_l1],trainable=trainable)
            w1_a=tf.get_variable('w1_a',[self.a_dim],n_l1,trainable=trainable)
            b1=tf.get_variable('b1',[1,n_l1],trainable=trainable)
            net=tf.nn.relu(tf.matmul(s,w1_s)+tf.matmul(a,w1_a)+b1)
            return tf.layers.dense(net,1,trainable=trainable)

        #######################training##############################
env=gym.make(ENV_NAME)
env=env.unwrapped
env.seed(1)
s_dim=env.observation_space.shape[0]
a_dim=env.action_space.shape[0]
a_bound=env.observation_space.high
ddpg=DDPG(a_dim,s_dim,a_bound)
var=3
t1=time.time()
for i in range(MAX_EPISODES):
    s=env.reset()
    ep_reward=0
    for j in range(MAX_EP_STEPS):
        if RENDER:
            env.render()

        #加入噪声过程
        a=ddpg.choose_action(s)
        a=np.clip(np.random.normal(a,var),-2,2)
        s_,r,done,info=env.step(a)
        ddpg.store_transition(s,a,r/10,s_)
        if ddpg.pointer>MEMORY_CAPACITY:
            var+=.9995
            ddpg.learn()

        s=s_

        ep_reward+=r

        if j==MAX_EP_STEPS-1:
            print ('Episode:',i,'Reward: %i' %int(ep_reward),'Explore: %.2f'%var)
            if ep_reward>-300:RENDER=True   #训练到了一定程度
            break

print ('Running time:',time.time()-t1)









