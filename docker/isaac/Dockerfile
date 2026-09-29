FROM nvcr.io/nvidia/isaac-sim:5.0.0

ARG UNITREE_SIM_COMMIT=e30c25b1dffdf92ada1d6c8c1fe9a47bdde0fecc
ARG ISAACLAB_COMMIT=46dff135f44683f031edf346e544fcfd8456b2bb
ARG CYCLONEDDS_COMMIT=5041f3560c088c99e5088b2b8520b69169621196
ARG UNITREE_SDK_COMMIT=814556d15970dd2ecf1c9984e845ca02ab07e206
ARG TELEIMAGER_COMMIT=b81de448bca9c696d7ce145f4af71c66146d0b69
ENV DEBIAN_FRONTEND=noninteractive

USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake curl git git-lfs openssl unzip ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && git lfs install --system

WORKDIR /opt
RUN mkdir IsaacLab \
    && curl -fsSL --retry 10 --retry-all-errors --connect-timeout 15 \
       "https://codeload.github.com/isaac-sim/IsaacLab/tar.gz/${ISAACLAB_COMMIT}" \
       | tar -xz --strip-components=1 -C IsaacLab \
    && cd IsaacLab \
    && ./isaaclab.sh --install

RUN mkdir cyclonedds \
    && curl -fsSL --retry 10 --retry-all-errors --connect-timeout 15 \
       "https://codeload.github.com/eclipse-cyclonedds/cyclonedds/tar.gz/${CYCLONEDDS_COMMIT}" \
       | tar -xz --strip-components=1 -C cyclonedds \
    && cmake -S cyclonedds -B cyclonedds/build -DCMAKE_INSTALL_PREFIX=/opt/cyclonedds/install \
    && cmake --build cyclonedds/build --target install -j2 \
    && echo /opt/cyclonedds/install/lib > /etc/ld.so.conf.d/cyclonedds.conf \
    && ldconfig
ENV CYCLONEDDS_HOME=/opt/cyclonedds/install

RUN mkdir unitree_sdk2_python \
    && curl -fsSL --retry 10 --retry-all-errors --connect-timeout 15 \
       "https://codeload.github.com/unitreerobotics/unitree_sdk2_python/tar.gz/${UNITREE_SDK_COMMIT}" \
       | tar -xz --strip-components=1 -C unitree_sdk2_python \
    && /isaac-sim/python.sh -m pip install --no-cache-dir -e /opt/unitree_sdk2_python

RUN mkdir unitree_sim_isaaclab \
    && curl -fsSL --retry 10 --retry-all-errors --connect-timeout 15 \
       "https://codeload.github.com/unitreerobotics/unitree_sim_isaaclab/tar.gz/${UNITREE_SIM_COMMIT}" \
       | tar -xz --strip-components=1 -C unitree_sim_isaaclab \
    && mkdir unitree_sim_isaaclab/teleimager \
    && curl -fsSL --retry 10 --retry-all-errors --connect-timeout 15 \
       "https://codeload.github.com/unitreerobotics/teleimager/tar.gz/${TELEIMAGER_COMMIT}" \
       | tar -xz --strip-components=1 -C unitree_sim_isaaclab/teleimager \
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
