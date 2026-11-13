# GPU加速工具研究與本機短測

2026-11-13，Codex。建議先使用現成CuPy＋CUDA Graph，保留研究自己的逐bit課程與特殊Adam轉接；目前沒有理由從零建整套CUDA訓練框架。已完成一個可測的薄原型，正式F2程式與模型未更動。

本機是GTX1650／4GB／SM7.5，現用CuPy14.2.0、CUDA12.9元件、NumPy2.3.5、Numba0.68.1，全部裝在獨立venv。驅動610.88不改；實際GPU矩陣運算與當前逐bit原型均有執行紀錄。

## 實測結果

相同32個合成binary-prefix／三類target循環，160→64(tanh)→3，10499參數；每一個target立即更新一次Adam，沒有合併多bit梯度。每方法3次，每次1024更新，中位數與全部三次範圍如下：

|方法|中位秒數|三次範圍|版本／範圍|
|---|---:|---|---|
|original_NumPy_string_CPU|0.488750|0.329399～0.900483|CPU control|
|preencoded_NumPy_CPU|0.926678|0.895790～0.982060|CPU control|
|Numba_njit_CPU_fastmath_false|0.661416|0.645712～0.677802|CPU control|
|CuPy_eager_reductions_GPU|5.122711|1.948076～5.393370|attempt04 FP64clip|
|CuPy_CUDA_Graph_GPU|0.304462|0.304300～0.470006|attempt04 FP64clip|

當前Graph對同運算eager的觀測中位比值為16.83；對原CPU中位為1.61。CPU波動大、區間與Graph重疊，不能當嚴格顯著性結論或把107分鐘完整實驗直接除以這個比值。計時包含同步完成與CPU排隊空檔，GPU events與wall都保留；不是只量非同步送出時間，也不是純GPU busy time。編譯／context／allocation-transfer／validation另列。原CPU包含字串encode與回傳pred，GPU沒有完整每target host trace/hash，所以還不是整個研究pipeline的同工比較。

原Numba移植沒有建立加速證據。最早直接CuPy+cuBLAS eager原型中位5.119203秒（attempt02），Graph卻在CuPy包裝層被拒絕；該舊prototype含較早clip cast，不能把它的time貼給現在source。完整歷史均保留。

## 為什麼這個GPU版本能跑

CuPy官方提供[Windows wheels及CUDA元件安裝](https://docs.cupy.dev/en/stable/install.html)，有[Stream capture與Graph](https://docs.cupy.dev/en/stable/reference/generated/cupy.cuda.Stream.html)。但v14.2的[cuBLAS包裝層setStream](https://github.com/cupy/cupy/blob/v14.2.0/cupy_backends/cuda/libs/cublas.pyx)明確拒絕capture內呼叫；本機trace正中此guard，不能推論CUDA/cuBLAS硬體本體不支援。

原型把所有小矩陣dot/outer改為CuPy broadcast product＋FP32 reduction後可capture；eager與Graph使用同一套運算。p/m/v就地更新，t與資料／標籤index在GPU上逐步前進；capture16個串行optimizer steps，replay沒有把它變成一次大batch更新。最終版移除了提早FP32clip cast，與原裁切生效時的FP64scalar規則對齊。CUDA核心與記憶體由現成庫管理，沒有自行寫一套autograd／CUDA runtime。

GTX1650屬Turing。NVIDIA[Graph launch文章](https://developer.nvidia.com/blog/constant-time-launch-for-straight-line-cuda-graphs-and-other-performance-enhancements/)的Ampere近常數launch數字不能直接套在此卡；這裡只採本機實測值。原套件中文路徑令NVRTC include失敗，指向同一venv的ASCII alias後實際運算成功；這是本機確認的workaround，不泛化成所有CUDA均不支援中文路徑。

## 正確性與本次邊界

fresh t0與aged t400500／異質birth各64步，當前GPU兩backend通過原定atol2e-5／rtol2e-5，最大learning-state abs誤差約4.98e-6，非byteexact。檢查19項p/m/v/birth/t/L/H末狀態；eager記64個輸出、Graph每case記第15/31/47/63四個logits/CE/argmax，共8個選定Graph輸出。Graph timed每1024步都實際t400500→401524，沒有拿capture錄製的80步當已執行更新。

兩合成初態m/v均為0；沒有測真父模型非零moments、RNG／growth／events／研究counter，沒有完整每target loss/pred hash、900題自由生成或全訓練重播。因此是加速候選的工程驗證，尚非完整正式backend移植驗收。獨立審查只核官方來源、程式與metadata，沒有獨立重跑神經計算或測速。

所有CPU控制與4個GPUattempt合計實際合成optimizer更新26,234；每有效backend最多6,411，符合原40000／7000上限，正式學習實驗更新0。attempt01是不支援take(mode)而0GPU更新；02包含失敗Graph的1次warm；03保留clip32原型；04才是當前clip64候選。沒有覆寫失敗或改容差。

## 工具取捨

CuPy／CUDA Graph：最接近現有NumPy及手寫Adam，這台機器已測通，適合先做可切換backend。必要時可用現成[RawKernel](https://docs.cupy.dev/en/stable/reference/generated/cupy.RawKernel.html)只補一小段已量到的熱點，不先寫整套底層。

PyTorch：官方[v2.15 release](https://github.com/pytorch/pytorch/releases/tag/v2.15.0)與Windows CUDA wheel支援本硬體作eager／CUDAGraph候選，但本輪未安裝或測速，不宣稱輸贏；stock Adam也不能悄悄取代每參數birth-age。當前upstream[Triton相容範圍](https://github.com/triton-lang/triton#compatibility)與原生Windows／SM7.5不直接吻合，不能由torch.compile API存在就保證GPU編譯路徑可用。

下一步先在模型副本整合完整state／每target trace／counter，做短同課序一致性及整段計時，再決定正式研究切換。更大加速要由profile指出小核心瓶頸後再寫，沒有宣稱本輪已證明手寫CUDA一定勝出。

當前source SHA `a5e2741ac7a49ec58a8dd63433dbfc3e87938febb334e8c9e1d6c19980461110`，當前結果SHA `8cd963fb60dab2e041176653b65fa26b422fccc99e32a3aa58b267993c2985f0`。來源、全部失敗與短測結果由publication manifest索引，runtime/venv/cache不入Git。固定外部隊員：NVIDIA真呼一次、候選結構拒絕未採；Gemini因既有analysis-only隔離未解明列skip，詳external-review.json。整份聊天、帳號quota、憑證均未外送。
