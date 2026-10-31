#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <objc/runtime.h>
#import <objc/message.h>
#include <string.h>
#include <stdio.h>

// Only descriptor objects: no Metal device, queue, kernel client or GPU command.
int main(void) { @autoreleasepool {
    Class c=objc_getClass("MTLRenderPipelineDescriptorInternal");
    Class a=objc_getClass("MTLRenderPipelineColorAttachmentDescriptorInternal");
    Ivar p=c?class_getInstanceVariable(c,"_private"):NULL;
    Ivar ap=a?class_getInstanceVariable(a,"_private"):NULL;
    const char *e=p?ivar_getTypeEncoding(p):NULL,*ae=ap?ivar_getTypeEncoding(ap):NULL;
    BOOL valid=e && strstr(e,"\"shaderValidation\"q\"shaderValidationState\"q\"textureWriteRoundingMode\"q") &&
        strstr(e,"\"alphaToCoverageEnabled\"b2\"alphaToOneEnabled\"b2") && ae &&
        strstr(ae,"\"blendingEnabled\"b2") && strstr(ae,"\"writeMask\"b5\"logicOpEnabled\"b1\"logicOp\"b4\"pixelFormat\"b22");
    printf("Render descriptor private encoding: %s\nAttachment private encoding: %s\n",e?:"missing",ae?:"missing");
    if(!valid)return 2;
    MTLRenderPipelineDescriptor *d=[MTLRenderPipelineDescriptor new];
    d.vertexDescriptor=[MTLVertexDescriptor vertexDescriptor];d.rasterSampleCount=4;
    const uint8_t *raw=((const void*(*)(id,SEL))objc_msgSend)(d,sel_registerName("_descriptorPrivate"));
    uint64_t count=0;void *vd=NULL;
    if(raw){memcpy(&count,raw+0xb8,8);memcpy(&vd,raw+0x110,8);}
    valid=raw && count==4 && vd==(__bridge void*)d.vertexDescriptor;
    [d release];puts(valid?"PASS: current Metal descriptor ABI matches the adapter.":"FAIL: Metal descriptor ABI differs.");
    return valid?0:3;
}}
