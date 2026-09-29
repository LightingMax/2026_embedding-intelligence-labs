FROM nvcr.io/nvidia/isaac-sim:5.0.0

ARG UNITREE_SIM_COMMIT=e30c25b1dffdf92ada1d6c8c1fe9a47bdde0fecc
ARG ISAACLAB_COMMIT=46dff135f44683f031edf346e544fcfd8456b2bb
ARG CYCLONEDDS_COMMIT=5041f3560c088c99e5088b2b8520b69169621196
ARG UNITREE_SDK_COMMIT=814556d15970dd2ecf1c9984e845ca02ab07e206
ARG TELEIMAGER_COMMIT=b81de448bca9c696d7ce145f4af71c66146d0b69
ENV DEBIAN_FRONTEND=noninteractive
ENV TERM=xterm

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake curl git git-lfs openssl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install --system

WORKDIR /opt
COPY external/isaac-deps/isaaclab.tar.gz /tmp/isaaclab.tar.gz
RUN mkdir IsaacLab \
    && tar -xzf /tmp/isaaclab.tar.gz --strip-components=1 -C IsaacLab \
    && rm /tmp/isaaclab.tar.gz \
    && cd IsaacLab \
    && ln -s /isaac-sim _isaac_sim \
    && ./isaaclab.sh --install none \
    && /isaac-sim/python.sh -m pip install --no-cache-dir --no-build-isolation "flatdict==4.0.1" \
    && /isaac-sim/python.sh -m pip install --no-cache-dir "gymnasium==1.2.0" "prettytable==3.3.0" \
    && /isaac-sim/python.sh -m pip install --no-cache-dir --no-deps -e /opt/IsaacLab/source/isaaclab

COPY external/isaac-deps/cyclonedds.tar.gz /tmp/cyclonedds.tar.gz
RUN mkdir cyclonedds \
    && tar -xzf /tmp/cyclonedds.tar.gz --strip-components=1 -C cyclonedds \
    && rm /tmp/cyclonedds.tar.gz \
    && cmake -S cyclonedds -B cyclonedds/build -DCMAKE_INSTALL_PREFIX=/opt/cyclonedds/install \
    && cmake --build cyclonedds/build --target install -j2 \
    && echo /opt/cyclonedds/install/lib > /etc/ld.so.conf.d/cyclonedds.conf \
    && ldconfig
ENV CYCLONEDDS_HOME=/opt/cyclonedds/install

COPY external/isaac-deps/unitree-sdk.tar.gz /tmp/unitree-sdk.tar.gz
RUN mkdir unitree_sdk2_python \
    && tar -xzf /tmp/unitree-sdk.tar.gz --strip-components=1 -C unitree_sdk2_python \
    && rm /tmp/unitree-sdk.tar.gz \
    && /isaac-sim/python.sh -m pip install --no-cache-dir \
       "numpy<2" "opencv-python<4.12" "cyclonedds==0.10.2" \
    && /isaac-sim/python.sh -m pip install --no-cache-dir --no-deps -e /opt/unitree_sdk2_python

COPY external/isaac-deps/unitree-sim.tar.gz /tmp/unitree-sim.tar.gz
COPY external/isaac-deps/teleimager.tar.gz /tmp/teleimager.tar.gz
RUN mkdir unitree_sim_isaaclab \
    && tar -xzf /tmp/unitree-sim.tar.gz --strip-components=1 -C unitree_sim_isaaclab \
    && mkdir -p unitree_sim_isaaclab/teleimager \
    && tar -xzf /tmp/teleimager.tar.gz --strip-components=1 -C unitree_sim_isaaclab/teleimager \
    && rm /tmp/unitree-sim.tar.gz /tmp/teleimager.tar.gz \
    && cd unitree_sim_isaaclab \
    && /isaac-sim/python.sh -m pip install --no-cache-dir -r requirements.txt \
    && /isaac-sim/python.sh -m pip install --no-cache-dir -e teleimager \
    && sed -i 's/type:.*/type: isaacsim/' teleimager/cam_config_server.yaml \
    && sed -i 's/image_shape:.*/image_shape: [480, 640]/' teleimager/cam_config_server.yaml \
    && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
       -subj '/CN=embodied-book-labs' -keyout /opt/unitree_sim_isaaclab/key.pem \
       -out /opt/unitree_sim_isaaclab/cert.pem

WORKDIR /opt/unitree_sim_isaaclab
COPY docker/isaac/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["smoke"]
