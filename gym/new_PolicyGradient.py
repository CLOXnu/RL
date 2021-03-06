import os
import gym
import numpy as np

from tensorflow.keras.layers import Input, Dense
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam
import tensorflow.keras.backend as K


class PG:
    def __init__(self):
        self.model = self.build_model()
        if os.path.exists('pg.h5'):
            self.model.load_weights('pg.h5')

        self.env = gym.make('CartPole-v0')
        # self.env = gym.make('MountainCar-v0')
        self.gamma = 0.95

    def build_model(self):
        """基本网络结构.
        """
        inputs = Input(shape=(4,), name='ob_input')
        x = Dense(10, activation='relu')(inputs)
        x = Dense(2, activation='relu')(x)
        x = Dense(1, activation='sigmoid')(x)

        model = Model(inputs=inputs, outputs=x)

        return model

    def loss(self, y_true, y_pred):
        """损失函数.
        Arguments:
            y_true: (action, reward)
            y_pred: action_prob

        Returns:
            loss: reward loss
        """
        action_pred = y_pred
        action_true, discount_episode_reward = y_true[:, 0], y_true[:, 1]
        # 二分类交叉熵损失
        action_true = K.reshape(action_true, (-1, 1))
        loss = K.binary_crossentropy(action_true, action_pred)
        # 乘上discount_reward
        loss = loss * K.flatten(discount_episode_reward)

        return loss

    def discount_reward(self, rewards):
        """Discount reward
        Arguments:
            rewards: 一次episode中的rewards
        """
        # 以时序顺序计算一次episode中的discount reward
        discount_rewards = np.zeros_like(rewards, dtype=np.float32)
        cumulative = 0.
        for i in reversed(range(len(rewards))):
            cumulative = cumulative * self.gamma + rewards[i]
            discount_rewards[i] = cumulative

        # normalization,有利于控制梯度的方差
        discount_rewards -= np.mean(discount_rewards)
        discount_rewards //= np.std(discount_rewards)

        return list(discount_rewards)

    def train(self, episode, batch):
        """训练
        Arguments:
            episode: 游戏次数
            batch： 一个batch包含几次episode，每个batch更新一次梯度

        Returns:
            history: 训练记录
        """
        self.model.compile(loss=self.loss, optimizer=Adam(lr=0.01))

        history = {'episode': [], 'Batch_reward': [], 'Episode_reward': [], 'Loss': []}

        episode_reward = 0
        states = []
        actions = []
        rewards = []
        discount_rewards = []

        for i in range(episode):
            observation = self.env.reset()
            erewards = []

            while True:
                self.env.render()
                x = observation.reshape(-1, 4)
                prob = self.model.predict(x)[0][0]
                # 根据随机概率选择action
                action = np.random.choice(np.array(range(2)), size=1, p=[1 - prob, prob])[0]
                observation, reward, done, _ = self.env.step(action)
                # 记录一个episode中产生的数据
                states.append(x[0])
                actions.append(action)
                erewards.append(reward)
                rewards.append(reward)

                if done:
                    # 一次episode结束后计算discount rewards
                    discount_rewards.extend(self.discount_reward(erewards))
                    break
            # 保存batch个episode的数据，用这些数据更新模型
            if i != 0 and i % batch == 0:
                batch_reward = sum(rewards)
                episode_reward = batch_reward / batch
                # 输入X为状态， y为action与discount_rewards，用来与预测出来的prob计算损失
                X = np.array(states)
                y = np.array(list(zip(actions, discount_rewards)))

                loss = self.model.train_on_batch(X, y)

                history['episode'].append(i)
                history['Batch_reward'].append(batch_reward)
                history['Episode_reward'].append(episode_reward)
                history['Loss'].append(loss)

                print('Episode: {} | Batch reward: {} | Episode reward: {} | loss: {:.3f}'.format(i, batch_reward,
                                                                                                  episode_reward, loss))

                episode_reward = 0
                states = []
                actions = []
                rewards = []
                discount_rewards = []

        self.model.save_weights('dpg.h5')

        return history

    def play(self):
        """使用训练好的模型测试游戏.
        """
        observation = self.env.reset()

        count = 0
        reward_sum = 0
        random_episodes = 0

        while random_episodes < 10:
            self.env.render()

            x = observation.reshape(-1, 4)
            prob = self.model.predict(x)[0][0]
            action = 1 if prob > 0.5 else 0
            observation, reward, done, _ = self.env.step(action)

            count += 1
            reward_sum += reward

            if done:
                print("Reward for this episode was: {}, turns was: {}".format(reward_sum, count))
                random_episodes += 1
                reward_sum = 0
                count = 0
                observation = self.env.reset()


if __name__ == '__main__':
    model = PG()
    history = model.train(200, 5)
    model.play()