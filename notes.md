
#### self-wiki  
* 数字孪生Reid AI  
    - 领英(LinkedIn)联合创始人、风投公司Greylock Partners合伙人雷德·霍夫曼(Reid Hoffman)主要将他的数字孪生Reid AI用于公开露面和媒体采访。该系统利用霍夫曼22年来的书籍、演讲、播客和文章进行了训练，自2024年推出以来，已发表了超过75次演讲和演示。不过，这些内容仍需人类协助准备。  

##### tasks  

- make    
    * # Sync stays local 
    > LLM_PROVIDER=mlx make sync 
    * # Query with Gemini (cloud)
    > LLM_PROVIDER=gemini make query
    * # Audit with Gemini (cloud)  
    >  LLM_PROVIDER=gemini make audit

- site
    > make query-web
    > http://100.90.225.26:5050/  
    
- backliner 
   - backliner.py
   - **Evolved from**: Your path of intellectual progress.
   - **Mentioned in**: Broad associations and context.
   - **Contradicts**: Points of cognitive friction.

##### the architecture
* Push intelligence up into skills, and push execution down into deterministic tooling. keep the harness thin.  
    - Fast skills sit on top
        + markdown procedures that **encode judgement, process, and domain knowledge** 
    - thin cli harness sits in the middle.
        + JSON in, text out. Read-only by default.
    - deterministic is where trust lives. 
        + Same input, same output. Every time. SQL queris. Compiled code. ARITHMETIC.

* a skill file tell the model how
    - works like a method call 

* the harness is the program that runs the LLM  
    - runs the model in a loop,
    reads and writes your files, manages context, and enforces safety.

* Resolvers tell it what to load and when  
    - The description is the resolver.
    Every skill has a description field, and the model matches user intent to skill descriptions automatically.

* latent space vs deterministic space  
    - latent spcae is where intelligence lives
    - deterministic is where trust lives  

* Diarization is the step that makes AI useful for real knowledge work

#### references
* [Thin Harness, Fat Skills](https://x.com/garrytan/status/2042925773300908103)
