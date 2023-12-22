# 多进程执行 GFPGAN  

1. 采用多进程 GFPGAN, 提高资源利用  
2. 去除了 `cropped_faces` 和 `restored_faces` 的无关的中间图片的保存
3. 根据自身设备修改进程池中的进程个数  
`inference-gfpgan.py` 中的第 `160` 行

```python
ctx = torch.multiprocessing.get_context("spawn")
pool = ctx.Pool(7)
pool.map(restore_mul, img_list)
```