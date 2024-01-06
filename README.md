 [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/mjavadpur/GFPGAN-Speed/blob/main/quick_demo.ipynb)

# Multiple processes execute GFPGAN

1. Use multi-process GFPGAN to improve resource utilization
2. Removed the saving of irrelevant intermediate images of `cropped_faces` and `restored_faces`
3. Modify the number of processes in the process pool according to your own equipment
Line `160` in `inference-gfpgan.py`

```python
ctx = torch.multiprocessing.get_context("spawn")
pool = ctx.Pool(7)
pool.map(restore_mul, img_list)
```

Result:
1. In colab with T4: inference_gfpgan_normal.py file 75s
2. In colab with T4: inference_gfpgan.py             92S
3. In colab With cpu inference_gfpgan_normal.py file 965s
4. In colab With cpu inference_gfpgan.py more than   500s (canceled)

