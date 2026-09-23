import numpy as np
import matplotlib.pyplot as plt

# 爱心参数方程
# x = 16sin³(t)
# y = 13cos(t) - 5cos(2t) - 2cos(3t) - cos(4t)
t = np.linspace(0, 2 * np.pi, 1000)
x = 16 * np.sin(t) ** 3
y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)

# 画图
plt.figure(figsize=(6, 6), dpi=100)
plt.plot(x, y, color='red', linewidth=2)
plt.fill(x, y, color='pink', alpha=0.6)
plt.axis('off')
plt.title('❤️', fontsize=20, pad=10)
plt.tight_layout()
plt.savefig('heart.png', dpi=150, bbox_inches='tight', pad_inches=0.1)
plt.show()
